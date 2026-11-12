"""loopback 평가 CLI 전용 Elasticsearch 7.10+/8/9 REST 어댑터."""

import json
import os
import re
from urllib.parse import urlsplit

import httpx

from app.rag.loader import digest
from app.rag.pipeline import canonical
from app.rag.scope import classify_question

QUALITY_POLICY = {
    "version": "bm25-quality-v2",
    "intentPolicy": "feature-purpose-rules-v1",
    "weightedFields": [
        "content",
        "content.ko",
        "articleTitle.ko^2",
        "featureNames^0.5",
        "article^4",
    ],
    "facetBoost": 3,
    "applicationBoost": 2,
    "nonApplicationSupplementWeight": 0.25,
    "views": {
        "body": ["LAW_BODY", "DECREE_BODY", "RULE_BODY"],
        "context": ["LAW_BODY", "DECREE_BODY", "RULE_BODY", "SUPPLEMENT"],
        "comparison": ["AMENDMENT_SUMMARY", "AMENDMENT_TEXT"],
    },
}


class EvaluationSearchError(RuntimeError):
    pass


def index_name(selection_hash, profile="baseline"):
    if not re.fullmatch(r"[a-f0-9]{64}", selection_hash):
        raise ValueError("선정 해시 형식이 다릅니다.")
    if profile not in {"baseline", "quality-v2"}:
        raise ValueError("평가 프로필이 다릅니다.")
    return (
        "hope-rag-eval-"
        + selection_hash
        + ("-quality-v2" if profile == "quality-v2" else "")
    )


MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "tokenizer": {
                "ko_grams": {
                    "type": "ngram",
                    "min_gram": 2,
                    "max_gram": 3,
                    "token_chars": ["letter", "digit"],
                }
            },
            "analyzer": {
                "ko_eval": {
                    "type": "custom",
                    "tokenizer": "ko_grams",
                    "filter": ["lowercase"],
                }
            },
        },
    },
    "mappings": {
        "dynamic": False,
        "properties": {
            "content": {
                "type": "text",
                "similarity": "BM25",
                "fields": {
                    "ko": {"type": "text", "analyzer": "ko_eval", "similarity": "BM25"}
                },
            },
            "article": {"type": "text"},
            "documentTitle": {"type": "text"},
            **{
                k: {"type": "keyword"}
                for k in (
                    "chunkId",
                    "id",
                    "documentVersion",
                    "selectionHash",
                    "usageScope",
                    "verificationStatus",
                    "duplicateGroup",
                    "topics",
                    "contentHash",
                )
            },
        },
    },
}

QUALITY_MAPPING = json.loads(json.dumps(MAPPING))
QUALITY_MAPPING["mappings"]["properties"].update(
    {
        "sourceKind": {"type": "keyword"},
        "legalVersions": {"type": "keyword"},
        "articleTitle": {
            "type": "text",
            "similarity": "BM25",
            "fields": {
                "ko": {"type": "text", "analyzer": "ko_eval", "similarity": "BM25"}
            },
        },
        "featureNames": {"type": "text", "analyzer": "ko_eval", "similarity": "BM25"},
    }
)


class EvaluationStore:
    def __init__(self, selection_hash, *, url=None, transport=None, profile="baseline"):
        url = url or os.environ.get("RAG_EVAL_ES_URL", "http://127.0.0.1:9200")
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "평가 서버는 인증정보 없는 loopback 기본 주소만 허용합니다."
            )
        self.selection_hash = selection_hash
        self.index = index_name(selection_hash, profile)
        self.profile = profile
        self.mapping = QUALITY_MAPPING if profile == "quality-v2" else MAPPING
        self.server_major = None
        self.client = httpx.Client(
            base_url=url.rstrip("/"),
            timeout=10,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    def close(self):
        self.client.close()

    def request(self, method, path, **kwargs):
        # 모든 데이터 요청은 생성자에서 고정한 평가 인덱스에만 보낸다.
        if path != "/" and not (
            path == "/" + self.index or path.startswith("/" + self.index + "/")
        ):
            raise ValueError("다른 인덱스 접근을 차단했습니다.")
        try:
            response = self.client.request(method, path, **kwargs)
            if response.status_code == 404:
                raise EvaluationSearchError("EVAL_INDEX_NOT_FOUND")
            response.raise_for_status()
            if (
                path != "/"
                and self.server_major != "7"
                and response.headers.get("x-elastic-product") != "Elasticsearch"
            ):
                raise EvaluationSearchError("ELASTICSEARCH_PRODUCT_NOT_CONFIRMED")
            data = response.json()
            if not isinstance(data, dict):
                raise EvaluationSearchError("INVALID_ELASTICSEARCH_RESPONSE")
            if (
                path == "/"
                and data.get("version", {}).get("number", "").split(".")[0]
                in {"8", "9"}
                and response.headers.get("x-elastic-product") != "Elasticsearch"
            ):
                raise EvaluationSearchError("ELASTICSEARCH_PRODUCT_NOT_CONFIRMED")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise EvaluationSearchError("EVAL_ELASTICSEARCH_REQUEST_FAILED") from exc

    def health(self):
        info = self.request("GET", "/")
        version = info.get("version", {}).get("number", "")
        parts = version.split(".")
        major = parts[0]
        if major not in {"7", "8", "9"} or (
            major == "7"
            and (len(parts) < 2 or not parts[1].isdigit() or int(parts[1]) < 10)
        ):
            raise EvaluationSearchError("UNSUPPORTED_ELASTICSEARCH_VERSION")
        if (
            info.get("tagline") != "You Know, for Search"
            or info.get("version", {}).get("distribution") == "opensearch"
        ):
            raise EvaluationSearchError("ELASTICSEARCH_PRODUCT_NOT_CONFIRMED")
        self.server_major = major
        return {
            "version": version,
            "product": "Elasticsearch",
            "transport": "httpx REST",
            "index": self.index,
        }

    def verify(self, documents):
        if self.server_major is None:
            self.health()
        meta = self.request("GET", "/" + self.index)
        mapping = meta.get(self.index, {}).get("mappings", {})
        actual_mapping = {k: v for k, v in mapping.items() if k != "_meta"}
        # 7.10은 dynamic=false를 문자열 "false"로 응답한다.
        if actual_mapping.get("dynamic") == "false":
            actual_mapping["dynamic"] = False
        if actual_mapping != self.mapping["mappings"]:
            raise EvaluationSearchError("INDEX_MAPPING_MISMATCH")
        expected = digest(canonical(documents).encode())
        if mapping.get("_meta") != {
            "selectionHash": self.selection_hash,
            "documentsHash": expected,
            "usageScope": "EVALUATION_ONLY",
        }:
            raise EvaluationSearchError("INDEX_IDENTITY_MISMATCH")
        count = self.request("GET", f"/{self.index}/_count")["count"]
        hits = self.request(
            "POST",
            f"/{self.index}/_search",
            json={"size": 1000, "query": {"match_all": {}}},
        )["hits"]["hits"]
        actual = {h["_id"]: h["_source"] for h in hits}
        if count != len(documents) or actual != {d["id"]: d for d in documents}:
            raise EvaluationSearchError("INDEX_CONTENT_MISMATCH")
        return {"count": count, "documentsHash": expected, "integrity": "PASS"}

    def index_documents(self, documents, *, reuse=False):
        self.health()
        for d in documents:
            if (
                d.get("usageScope") != "EVALUATION_ONLY"
                or d.get("verificationStatus") != "UNVERIFIED"
                or d.get("selectionHash") != self.selection_hash
            ):
                raise ValueError("선정된 평가 문서만 색인할 수 있습니다.")
        if len(documents) > 1000 or len({d["id"] for d in documents}) != len(documents):
            raise ValueError("평가 적재 크기 또는 ID가 다릅니다.")
        try:
            self.request("GET", "/" + self.index)
        except EvaluationSearchError as exc:
            if str(exc) != "EVAL_INDEX_NOT_FOUND":
                raise
        else:
            if reuse:
                return self.verify(documents)
            raise EvaluationSearchError("INDEX_EXISTS_USE_REUSE_OR_NEW_SELECTION")
        body = json.loads(json.dumps(self.mapping))
        body["mappings"]["_meta"] = {
            "selectionHash": self.selection_hash,
            "documentsHash": digest(canonical(documents).encode()),
            "usageScope": "EVALUATION_ONLY",
        }
        self.request("PUT", "/" + self.index, json=body)
        lines = []
        for d in documents:
            lines.extend((canonical({"create": {"_id": d["id"]}}), canonical(d)))
        response = self.request(
            "POST",
            f"/{self.index}/_bulk?refresh=wait_for",
            content="\n".join(lines) + "\n",
            headers={"Content-Type": "application/x-ndjson"},
        )
        if response.get("errors") or any(
            v.get("create", {}).get("status", 500) >= 300
            for v in response.get("items", [])
        ):
            raise EvaluationSearchError("BULK_PARTIAL_FAILURE_INDEX_NOT_READY")
        return self.verify(documents)

    def search(self, query, *, size=10, deduplicate=True, _payload=None):
        if self.server_major is None:
            self.health()
        if (
            not isinstance(query, str)
            or not query.strip()
            or len(query) > 1000
            or not 1 <= size <= 100
        ):
            raise ValueError("평가 질의 또는 결과 수가 다릅니다.")
        payload = {
            "size": 1000,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"usageScope": "EVALUATION_ONLY"}},
                        {"term": {"verificationStatus": "UNVERIFIED"}},
                        {"term": {"selectionHash": self.selection_hash}},
                    ],
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "content",
                                    "content.ko",
                                    "article^4",
                                    "documentTitle^2",
                                ],
                            }
                        }
                    ],
                }
            },
        }
        if _payload is not None:
            payload = _payload
        hits = self.request("POST", f"/{self.index}/_search", json=payload)["hits"][
            "hits"
        ]
        results = []
        groups = {}
        for hit in sorted(hits, key=lambda h: (-(h.get("_score") or 0), h["_id"])):
            source = hit["_source"]
            if (
                source.get("usageScope") != "EVALUATION_ONLY"
                or source.get("selectionHash") != self.selection_hash
                or source.get("verificationStatus") != "UNVERIFIED"
            ):
                raise EvaluationSearchError("SEARCH_BOUNDARY_VIOLATION")
            if digest(source.get("content", "").encode()) != source.get("contentHash"):
                raise EvaluationSearchError("SEARCH_CONTENT_CHANGED")
            row = {"score": hit["_score"], **source}
            group = source["duplicateGroup"] if deduplicate else hit["_id"]
            if group in groups:
                groups[group]["variants"].append(row)
            else:
                entry = {**row, "variants": []}
                results.append(entry)
                groups[group] = entry
        return results[:size]

    def search_evaluation(
        self, query, *, view="context", ranking="weighted", enforce_scope=True, size=10
    ):
        """분류·출처 필터·의미 필드를 사용하는 평가 전용 결과. 법적 사용 승인은 아니다."""
        if (
            self.profile != "quality-v2"
            or view not in {"all", "body", "context", "comparison"}
            or ranking not in {"baseline", "weighted"}
        ):
            raise ValueError("검색 비교 설정이 다릅니다.")
        intent = classify_question(query)
        retrieval_query = intent.get("normalizedQuery", query)
        if enforce_scope and intent["status"] != "IN_SCOPE":
            return {
                "status": intent["status"],
                "intent": intent,
                "hits": [],
                "answerUseAllowed": False,
            }
        filters = [
            {"term": {"usageScope": "EVALUATION_ONLY"}},
            {"term": {"verificationStatus": "UNVERIFIED"}},
            {"term": {"selectionHash": self.selection_hash}},
        ]
        if enforce_scope:
            filters.append({"terms": {"topics": intent["topics"]}})
        kinds = QUALITY_POLICY["views"]
        if view in kinds:
            filters.append({"terms": {"sourceKind": kinds[view]}})
        fields = ["content", "content.ko", "article^4", "documentTitle^2"]
        should = []
        if ranking == "weighted":
            fields = QUALITY_POLICY["weightedFields"]
            # 특정 조문/질문 ID가 아니라 일반적 질문 목적과 법령 단계의 관계만 사용한다.
            preferred = (
                "RULE_BODY"
                if "DOCUMENT" in intent["facets"]
                else "DECREE_BODY"
                if "DEFINITION" in intent["facets"]
                else "LAW_BODY"
                if "LIMIT" in intent["facets"]
                else None
            )
            if preferred:
                should.append(
                    {
                        "constant_score": {
                            "filter": {"term": {"sourceKind": preferred}},
                            "boost": QUALITY_POLICY["facetBoost"],
                        }
                    }
                )
            if "APPLICATION" in intent["facets"]:
                should.append(
                    {
                        "constant_score": {
                            "filter": {"term": {"sourceKind": "SUPPLEMENT"}},
                            "boost": QUALITY_POLICY["applicationBoost"],
                        }
                    }
                )
        payload = {
            "size": 1000,
            "query": {
                "bool": {
                    "filter": filters,
                    "must": [
                        {"multi_match": {"query": retrieval_query, "fields": fields}}
                    ],
                    "should": should,
                }
            },
        }
        if ranking == "weighted" and "APPLICATION" not in intent["facets"]:
            # 일반 요건/한도 질문에서는 짧은 공통 시행일이 본문을 밀어내지 않게 한다.
            # 적용시기 질문에는 감점을 적용하지 않으며 부칙 자체를 제거하지 않는다.
            payload["query"] = {
                "function_score": {
                    "query": payload["query"],
                    "functions": [
                        {
                            "filter": {"term": {"sourceKind": "SUPPLEMENT"}},
                            "weight": QUALITY_POLICY["nonApplicationSupplementWeight"],
                        }
                    ],
                    "score_mode": "multiply",
                    "boost_mode": "multiply",
                }
            }
        hits = self.search(query, size=size, _payload=payload)
        # 서버 필터 오류/잘못된 인덱스 응답도 비교자료를 본문처럼 노출시키지 않는다.
        for hit in hits:
            for item in [hit, *hit.get("variants", [])]:
                if view in kinds and item.get("sourceKind") not in kinds[view]:
                    raise EvaluationSearchError("SOURCE_VIEW_BOUNDARY_VIOLATION")
                if enforce_scope and not set(item["topics"]) & set(intent["topics"]):
                    raise EvaluationSearchError("TOPIC_BOUNDARY_VIOLATION")
            hit["answerUseAllowed"] = False
            hit["versionResolution"] = "NOT_VERIFIED"
        return {
            "status": "RETRIEVED_UNVERIFIED" if hits else "INSUFFICIENT_EVIDENCE",
            "intent": intent,
            "hits": hits,
            "answerUseAllowed": False,
        }
