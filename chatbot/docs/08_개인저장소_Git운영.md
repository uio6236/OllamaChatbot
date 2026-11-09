# 08. 개인 저장소 Git 운영 및 팀 기능 브랜치 통합

## 1. 실제 저장소 구조 (2026-11-09 사용자 결정)

| 역할 | 주소/경로 | 사용 시점 |
|---|---|---|
| 팀 초기 코드 | `KH-Team2/two-trillion` → `feature/project-base` | 최초 파일 복사 기준 |
| 팀 로컬 사본 | `C:\workspace\two-trillion` | 초기 원본 참고; Codex의 수정 대상 아님 |
| 개인 GitHub | `uio6236/OllamaChatbot` (별도 신규 저장소; Fork 아님) | AI 기능 전체 개발·테스트·커밋 |
| 개인 로컬 개발 | `C:\workspace\OllamaChatbot` | VS Code/Codex 작업 루트 |
| 팀 기능 브랜치 | `KH-Team2/two-trillion` → `feature/chatbot` | 완성 기능의 팀 반영 |
| 팀 통합 | `develop` → `main` | 팀 검토 및 최종 통합 |

**주의:** 개인 저장소와 팀 저장소의 Git 이력은 다르다. 개인 저장소의 `main` 전체를 팀의 `develop`에 직접 병합하는 방식은 사용하지 않는다.

## 2. 개인 저장소에 팀 초기 파일 넣기

이미 개인 GitHub `OllamaChatbot`을 Clone했다는 전제. 팀 초기 폴더와 개인 폴더가 모두 `C:\workspace` 아래에 있는지 확인한다.

Windows PowerShell에서:

```powershell
robocopy "C:\workspace\two-trillion" "C:\workspace\OllamaChatbot" /E /XD .git .metadata .venv node_modules target build dist .idea .vscode /XF .env .env.local .env.development.local .env.production.local
cd C:\workspace\OllamaChatbot
git remote -v
git status
```

- `robocopy` 종료 코드 1 등은 파일 복사 성공을 나타낼 수도 있다. 출력 내용을 확인한다.
- 기존 개인 저장소에 수정한 파일이 있다면 덮어쓰지 말고 먼저 비교한다.
- 복사 후 `.gitignore`를 확인하고 `git add` 전 `git status`로 보안 파일/로컬 생성물이 없는지 검토한다.
- **개인 저장소가 Public**이므로 비밀정보·개인 데이터 및 팀 비공개 자료 유출 금지. RAG 법령 PDF의 배포/공유 조건도 확인한다.

```powershell
# 실제 모든 변경 파일을 검토한 뒤, 사용자가 결정한 경우에만 수행
git add .
git diff --cached --stat
git diff --cached --check
# 이후 직접 또는 명시적 승인 받은 경우에만 commit/push
git commit -m "chore: import initial team project"
git push origin main
```

`git remote -v`의 origin은 개인 저장소를 가리켜야 한다. 팀 저장소의 `.git` 폴더를 복사하지 않는다.

## 3. Codex가 작업하는 위치와 권한

- VS Code로 **`C:\workspace\OllamaChatbot` 루트를 연다.** `chatbot/` 하위만 단독으로 열지 않는다. Backend/Frontend를 함께 분석·수정해야 하기 때문이다.
- 현재 작업 브랜치는 개인 `main`을 사용해도 되고, 개인 `dev/chatbot-rag`를 별도 생성해도 된다. **팀 브랜치인 `feature/chatbot`과 혼동하지 않는다.**
- Codex는 먼저 현재 `AGENTS.md`와 변경사항을 분석하고 작업 계획을 보고한다. 수정·커밋·Push·PR은 사용자 요청 범위에서만 한다.
- Calc, 공용 Security, 타 팀 기능 변경은 해당 기능에 필수적인 최소 수정으로 제한한다.

## 4. 완성된 기능을 팀 저장소에 반영하는 원칙

1. 팀 저장소의 최신 `develop` 또는 팀이 지정한 기준 브랜치를 로컬에서 확보한다.
2. 그 최신 기준에서 팀 저장소의 `feature/chatbot` 브랜치를 생성하거나 기존 브랜치를 최신화한다.
3. 개인 저장소에서 변경한 **챗봇 관련 파일만 선별**한다. `chatbot/` 신규 코드뿐 아니라 `backend/chat/`, 해당 Mapper/설정, React 챗봇 API 연동, 관련 문서 포함.
4. 파일을 무조건 덮어쓰지 말고 팀의 최신 공통 Security·환경 설정·프론트 서비스와 비교·병합한다.
5. 팀 브랜치에서 Backend/Frontend/Chatbot 테스트를 수행한다.
6. 팀 `feature/chatbot`에서 `develop` 대상으로 PR. 승인·통합 후 최종 전체 테스트를 거쳐 `main` 반영은 팀이 결정한다.

**중요:** 개인 저장소의 전체 코드를 팀 최신 브랜치에 복사하지 않는다. Git 이력이 다르므로 일반적인 브랜치 간 빠른 병합으로 해결되지 않는다. 코드 변경분은 비교·패치·파일별 반영 등의 절차로 이식한다.

## 5. 개발 시작 전 점검 체크리스트

- [ ] VS Code에서 연 폴더가 개인 `OllamaChatbot`인지
- [ ] 개인 저장소 `origin` URL이 일치하는지
- [ ] `chatbot/`, `backend/`, `frontend/`가 들어 있는지
- [ ] `.env`, 키, 비밀번호, 가상환경, 빌드 산출물 등 Git 제외 확인
- [ ] 기존 `AGENTS.md`를 원본 그대로 보존했고 추가 규칙 병합은 별도 검토하는지
- [ ] 최초 Codex 프롬프트는 **분석 전용**으로 실행하는지
