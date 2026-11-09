> 이 파일은 버전 10 추출 당시 원본 경로 대응 이력입니다. 이번 변경은 FEEDBACK_REPORT.md가 현재 기준입니다.

# 원본 코드와 추출 파일 대응표

실제 배포 버전 10, 커밋 `8113b52711cd46caf1d1e2c25bb51545599f16ab`에서 추출했습니다. 사이트 소스 저장소의 상태를 수정하지 않았습니다.

## 기존 파일의 JSX/JavaScript 변환

| 원본                                 | 추출 파일                                  |
| ------------------------------------ | ------------------------------------------ |
| `components/Dashboard.tsx`           | `src/pages/dashboard/Dashboard.jsx`        |
| `components/TaxInfoForm.tsx`         | `src/pages/tax/TaxInfoForm.jsx`            |
| `components/GroupStats.tsx`          | `src/pages/statistics/GroupStats.jsx`      |
| `components/AccountForms.tsx`        | `src/pages/auth/AccountForms.jsx`          |
| `components/AdminTools.tsx`          | `src/pages/admin/AdminTools.jsx`           |
| `components/ProfileDetails.tsx`      | `src/pages/profile/ProfileDetails.jsx`     |
| `components/ChatPanel.tsx`           | `src/pages/chatbot/ChatPanel.jsx`          |
| `components/ExpenseUpload.tsx`       | `src/components/expense/ExpenseUpload.jsx` |
| `lib/services.ts`                    | `src/api/services.js`                      |
| `lib/account-service.ts`             | `src/api/account-service.js`               |
| `lib/expense-service.ts`             | `src/api/expense-service.js`               |
| `lib/prototype-records.ts`           | `src/api/prototype-records.js`             |
| `lib/erd-contract.ts`                | `src/api/erd-contract.js`                  |
| `lib/dashboard-model.ts`             | `src/utils/dashboard-model.js`             |
| `lib/group-model.ts`                 | `src/utils/group-model.js`                 |
| `lib/utils.ts`                       | `src/utils/cn.js`                          |
| `components/ui/accordion.tsx`        | `src/components/ui/accordion.jsx`          |
| `components/ui/alert-dialog.tsx`     | `src/components/ui/alert-dialog.jsx`       |
| `components/ui/alert.tsx`            | `src/components/ui/alert.jsx`              |
| `components/ui/aspect-ratio.tsx`     | `src/components/ui/aspect-ratio.jsx`       |
| `components/ui/attachment.tsx`       | `src/components/ui/attachment.jsx`         |
| `components/ui/avatar.tsx`           | `src/components/ui/avatar.jsx`             |
| `components/ui/badge.tsx`            | `src/components/ui/badge.jsx`              |
| `components/ui/breadcrumb.tsx`       | `src/components/ui/breadcrumb.jsx`         |
| `components/ui/bubble.tsx`           | `src/components/ui/bubble.jsx`             |
| `components/ui/button-group.tsx`     | `src/components/ui/button-group.jsx`       |
| `components/ui/button.tsx`           | `src/components/ui/button.jsx`             |
| `components/ui/calendar.tsx`         | `src/components/ui/calendar.jsx`           |
| `components/ui/card.tsx`             | `src/components/ui/card.jsx`               |
| `components/ui/carousel.tsx`         | `src/components/ui/carousel.jsx`           |
| `components/ui/chart.tsx`            | `src/components/ui/chart.jsx`              |
| `components/ui/checkbox.tsx`         | `src/components/ui/checkbox.jsx`           |
| `components/ui/collapsible.tsx`      | `src/components/ui/collapsible.jsx`        |
| `components/ui/combobox.tsx`         | `src/components/ui/combobox.jsx`           |
| `components/ui/command.tsx`          | `src/components/ui/command.jsx`            |
| `components/ui/context-menu.tsx`     | `src/components/ui/context-menu.jsx`       |
| `components/ui/dialog.tsx`           | `src/components/ui/dialog.jsx`             |
| `components/ui/direction.tsx`        | `src/components/ui/direction.jsx`          |
| `components/ui/drawer.tsx`           | `src/components/ui/drawer.jsx`             |
| `components/ui/dropdown-menu.tsx`    | `src/components/ui/dropdown-menu.jsx`      |
| `components/ui/empty.tsx`            | `src/components/ui/empty.jsx`              |
| `components/ui/field.tsx`            | `src/components/ui/field.jsx`              |
| `components/ui/form.tsx`             | `src/components/ui/form.jsx`               |
| `components/ui/hover-card.tsx`       | `src/components/ui/hover-card.jsx`         |
| `components/ui/input-group.tsx`      | `src/components/ui/input-group.jsx`        |
| `components/ui/input-otp.tsx`        | `src/components/ui/input-otp.jsx`          |
| `components/ui/input.tsx`            | `src/components/ui/input.jsx`              |
| `components/ui/item.tsx`             | `src/components/ui/item.jsx`               |
| `components/ui/kbd.tsx`              | `src/components/ui/kbd.jsx`                |
| `components/ui/label.tsx`            | `src/components/ui/label.jsx`              |
| `components/ui/marker.tsx`           | `src/components/ui/marker.jsx`             |
| `components/ui/menubar.tsx`          | `src/components/ui/menubar.jsx`            |
| `components/ui/message-scroller.tsx` | `src/components/ui/message-scroller.jsx`   |
| `components/ui/message.tsx`          | `src/components/ui/message.jsx`            |
| `components/ui/native-select.tsx`    | `src/components/ui/native-select.jsx`      |
| `components/ui/navigation-menu.tsx`  | `src/components/ui/navigation-menu.jsx`    |
| `components/ui/pagination.tsx`       | `src/components/ui/pagination.jsx`         |
| `components/ui/popover.tsx`          | `src/components/ui/popover.jsx`            |
| `components/ui/progress.tsx`         | `src/components/ui/progress.jsx`           |
| `components/ui/radio-group.tsx`      | `src/components/ui/radio-group.jsx`        |
| `components/ui/resizable.tsx`        | `src/components/ui/resizable.jsx`          |
| `components/ui/scroll-area.tsx`      | `src/components/ui/scroll-area.jsx`        |
| `components/ui/select.tsx`           | `src/components/ui/select.jsx`             |
| `components/ui/separator.tsx`        | `src/components/ui/separator.jsx`          |
| `components/ui/sheet.tsx`            | `src/components/ui/sheet.jsx`              |
| `components/ui/sidebar.tsx`          | `src/components/ui/sidebar.jsx`            |
| `components/ui/skeleton.tsx`         | `src/components/ui/skeleton.jsx`           |
| `components/ui/slider.tsx`           | `src/components/ui/slider.jsx`             |
| `components/ui/sonner.tsx`           | `src/components/ui/sonner.jsx`             |
| `components/ui/spinner.tsx`          | `src/components/ui/spinner.jsx`            |
| `components/ui/switch.tsx`           | `src/components/ui/switch.jsx`             |
| `components/ui/table.tsx`            | `src/components/ui/table.jsx`              |
| `components/ui/tabs.tsx`             | `src/components/ui/tabs.jsx`               |
| `components/ui/textarea.tsx`         | `src/components/ui/textarea.jsx`           |
| `components/ui/toggle-group.tsx`     | `src/components/ui/toggle-group.jsx`       |
| `components/ui/toggle.tsx`           | `src/components/ui/toggle.jsx`             |
| `components/ui/tooltip.tsx`          | `src/components/ui/tooltip.jsx`            |
| `hooks/use-mobile.ts`                | `src/hooks/use-mobile.js`                  |

## 큰 원본 페이지에서 분리한 화면

`app/page.tsx`의 각 JSX 표현을 그대로 분리하고 기존 클로저 변수를 props로 전달했습니다. 별도 DOM 감싸기를 추가하지 않았습니다. `App.jsx`에는 공통 상태·세션 복원·계산·페이지 이동 처리를 남겼습니다.

| 분리 컴포넌트    | 파일                                      |
| ---------------- | ----------------------------------------- |
| `DashboardPage`  | `src/pages/dashboard/DashboardPage.jsx`   |
| `SimulationPage` | `src/pages/simulation/SimulationPage.jsx` |
| `ChatbotPage`    | `src/pages/chatbot/ChatbotPage.jsx`       |
| `BenefitsPage`   | `src/pages/tax/BenefitsPage.jsx`          |
| `StatisticsPage` | `src/pages/statistics/StatisticsPage.jsx` |
| `ProfilePage`    | `src/pages/profile/ProfilePage.jsx`       |
| `SupportPage`    | `src/pages/support/SupportPage.jsx`       |
| `AdminPage`      | `src/pages/admin/AdminPage.jsx`           |
| `PublicHeader`   | `src/components/layout/PublicHeader.jsx`  |
| `HomePage`       | `src/pages/home/HomePage.jsx`             |
| `AuthPage`       | `src/pages/auth/AuthPage.jsx`             |
| `Sidebar`        | `src/components/layout/Sidebar.jsx`       |
| `Topbar`         | `src/components/layout/Topbar.jsx`        |
| `TaxInputPage`   | `src/pages/tax/TaxInputPage.jsx`          |

## 그대로 복사하거나 실행용으로 바꾼 파일

- `public/favicon.svg`: 원본 복사. 로고는 CSS, 아이콘은 원본 버전의 lucide-react입니다.
- `data/statistics/*` → `src/data/statistics/*`: 통계 원본/정제 스냅샷 복사. `stat-file.json`의 파일 경로는 이동 위치에 맞춰 `src/`만 붙였습니다. 테이블/컬럼명·통계값은 바꾸지 않았습니다.
- `app/globals.css` → `src/styles/globals.css`: 원본 스타일 규칙 전체를 Prettier로 포맷했습니다.
- `app/layout.tsx`: HTML lang/title/description/스타일 연결을 `index.html`과 `src/main.jsx`에 반영했습니다.
- `vite.config.js`, `postcss.config.js`, npm 스크립트: 원본 배포 런타임을 일반 Vite 실행으로 대체한 구성입니다.
- `scripts/refresh-group-stat.mjs`: 기존 스크립트의 기준 폴더를 이동된 `src/data/statistics`로 맞췄습니다.
- `tests/prototype-flows.mjs`: 기존 서비스 검증 내용을 유지하고 TypeScript 임시 변환을 JavaScript 번들 검증으로 바꿨습니다. Windows 동적 import는 file URL로 처리합니다.

## 프론트엔드 실행에 사용되지 않아 제외한 원본 런타임

- `.openai/hosting.json`, Vinext/Cloudflare 전용 Vite 플러그인·Worker·실행 도우미·배포 산출물: 원본 호스팅 환경 전용이며 일반 Vite 화면과 무관합니다.
- `app/chatgpt-auth.ts`, `lib/connectors.ts`, `lib/connector-context.ts`, `lib/connector-contract.mts`, `lib/connector-errors.mts`, `lib/connector-preview.d.ts`, `components/connector-error.tsx`: 원본 현재 서비스 화면에서 호출하지 않는 호스트 인증/커넥터 스캐폴딩입니다. 실제 Spring Boot 또는 Gemma3 API를 대신하는 코드가 아닙니다.
- `db/`, `drizzle/`, `drizzle.config.ts`, `worker/`, `examples/`: 현재 희망환급 서비스가 연동하지 않는 배포 템플릿/샘플입니다. 추출본에서 새 Oracle 테이블을 만들거나 기존 ERD를 변경하지 않았습니다.
- Next/Vinext·Cloudflare·Drizzle 관련 의존성/타입 설정은 이와 함께 제외했습니다. 현재 프론트엔드와 보관 UI 컴포넌트가 쓰는 의존성은 원본 설치 버전으로 고정했습니다.
- `node_modules`, `dist`, `.git`, 개인 환경변수·토큰·브라우저 저장 데이터는 ZIP에 넣지 않았습니다.

이 대응표는 일반 React 개발용 프로젝트로의 이식 범위를 설명합니다. 원본 서버 배포 래퍼까지 동일한 프레임워크 프로젝트라는 의미는 아닙니다.
