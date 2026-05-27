# 💻 코다리 — 매수자가 '카톡 보내기' 버튼을 누르는 순간, 해당 액션을 추적하고 기록하는 백엔드 시스템 아키텍처와 API 명세서(Spec)를 설계해 주세요. 이 시스템은 다음 기능을 반드시 수행해야 합니다: 1. 클라이언트 측에서 리드 발생 시점의 메타데이터 (사용자 ID/익명화된 IP, 매물 ID, 시간 등)를 안전하게 수집합니다. 2. 백엔드 게이트웨이에서 해당 데이터를 받아 'Lead Event'로 기록하고, 공인중개사에게 알림(Notification API)을 트리거 합니다. 3. 이 과정에서 개인정보 보호법을 준수하며, 데이터가 유출되지 않도록 처리하는 보안 및 인증 로직도 함께 명시해야 합니다.

💻 코다리: 작업 시작합니다. 이 정도의 핵심 비즈니스 로직이라면, 단순히 기능만 구현하는 수준을 넘어선 아키텍처 레벨의 검증이 필수입니다. "어떻게 트래픽이 몰릴 때 병목 현상이 생기지 않나?", "개인정보가 누출될 위험은 없나?" 이 두 가지 관점에서 전체 시스템을 설계해야 합니다.

요청하신 '매수자 카톡 보내기 액션 추적 시스템'은 단순한 로깅(Logging)이 아니라, 핵심 수익 모델과 직결된 **Lead Management System (LMS)**의 첫 단계입니다. 따라서 아키텍처는 높은 신뢰성, 확장성, 그리고 법적 준수성을 최우선으로 고려해야 합니다.

제가 현재 프로젝트 구조와 일관되게, 이 시스템에 대한 상세한 기술 명세서(Technical Specification)를 설계하겠습니다.

---

# 🛠️ Lead Event Tracking System (LTS) 설계 명세서

## 1. 개요 및 목표
*   **목표:** 매수자(End-User)가 특정 매물(Listing ID)에 대해 공인중개사에게 연락 의사를 밝히는 핵심 액션(KakaoTalk Send)을 트래킹하고, 이를 플랫폼의 주요 리드 이벤트(`Lead Event`)로 표준화하여 기록합니다.
*   **핵심 가치:** 단순한 클릭 카운트를 넘어, **'연락 의도 발생 시점'** 이라는 법적/비즈니스 가치를 포착하여 공인중개사에게 실시간 알림을 제공하고 유료 전환의 근거로 삼습니다.
*   **아키텍처 패턴:** 비동기 이벤트 기반 아키텍처 (Event-Driven Architecture) 채택. 높은 트래픽 분산과 강한 결합도 방지가 목적입니다.

## 2. 시스템 구성 요소 및 데이터 흐름 (Data Flow Diagram Conceptual)

| 구성 요소 | 기술 스택/역할 | 주요 기능 | 검증 포인트 |
| :--- | :--- | :--- | :--- |
| **Client Frontend** | React/Vue + JavaScript | 카톡 버튼 클릭 시, 필요한 최소 메타데이터를 수집하여 API Gateway로 전송. (AJAX POST) | 사용자 인터랙션 추적의 정확성 확보 (Tracking Pixel 오염 방지). |
| **API Gateway (Backend)** | Nginx / AWS API Gateway | 모든 인바운드 요청을 받아 인증(AuthN), 권한 검증(AuthZ), 그리고 초기 데이터 유효성 검사 수행. | Rate Limiting, IP/Origin 체크를 통한 비정상 접근 차단. |
| **Ingestion Service (핵심)** | Python / GoLang Microservice | 1. 수신된 Raw 데이터를 표준화하고 정제(Sanitization)합니다. 2. 개인 식별 정보를 즉시 마스킹/익명화 처리(Pseudonymization). 3. 이벤트 스트림에 발행(`Lead Event`). | **PIPA 준수 로직이 가장 중요함.** 데이터가 DB에 저장되기 전 변환 필수. |
| **Event Stream** | Kafka / RabbitMQ | `Raw Lead Event`를 비동기적으로 수신하고, 여러 다운스트림 시스템(DB, Notification, Analytics)으로 분배합니다. | 메시지 영속성 및 순서 보장 (Exactly-Once Processing). |
| **Persistence Service** | DB Worker Microservice | 이벤트 스트림에서 데이터를 소비하여 최종 데이터베이스에 저장합니다. 리드 스코어링 로직 실행 지점입니다. | 중복 기록 방지 (Idempotency Key 사용). |
| **Notification Service** | Webhook/Worker | `Lead Event`를 구독하고, 공인중개사(Agent)의 계정 정보와 매칭하여 알림 API 호출을 트리거합니다. | 장애 발생 시 재시도 로직 (Exponential Backoff Retry) 필수. |

## 3. 상세 API 명세서 (API Spec)

### A. 클라이언트 측 액션 (Frontend Action)
*   **액션:** `KakaoTalk Send` 버튼 클릭.
*   **전송 방식:** Asynchronous POST Request (`/api/v1/leads/track`).
*   **메타데이터 수집 원칙:** 브라우저가 제공하는 정보만 사용하며, 사용자 동의를 받은 경우에만 ID 기반 추적을 시도합니다.

### B. 백엔드 API 엔드포인트 (Ingestion Gateway)
*   **요청 URL:** `POST https://api.redevelop-platform.com/v1/leads/track`
*   **헤더 필수 요소:**
    *   `Content-Type: application/json`
    *   `Authorization: Bearer <Token>` (API 호출 유효성 검증용)
*   **요청 Body (JSON Payload):**

```json
{
  "listingId": "LST-202405-1234",      // 매물 고유 ID (필수)
  "timestampClient": "2024-06-10T10:30:00Z", // 클라이언트 측 시간 기록 (UTC 권장)
  "actionType": "KAKAOTALK_SEND",     // 액션 유형 명시 (확장성 대비)
  "clientMetadata": {                   // 개인 식별 정보를 최소화하여 수집
    "pseudoUserId": "anon-uuid-xxxxxxxx", // 익명화된 사용자 ID 또는 쿠키 기반 UUID
    "sourceIpAnon": "192.0.2.1",          // IP 주소의 앞부분만 마스킹 (PIPA 준수)
    "userAgentString": "Mozilla/5.0..."   // 브라우저 정보 (분석용)
  }
}
```

*   **응답 Code:**
    *   `202 Accepted`: 요청을 정상적으로 수신하고 비동기 처리 큐에 넣었음. **(가장 중요)** 클라이언트는 이 코드를 받으면 성공으로 판단합니다. (즉시 DB 처리가 아님을 명시)
    *   `400 Bad Request`: 필수 필드 누락 또는 데이터 형식 오류.
    *   `429 Too Many Requests`: Rate Limiting에 걸림.

## 4. 보안 및 법적 준수 로직 (Critical Section)

이 부분은 개발자가 가장 주의해야 할 지점이며, 코드를 짜기 전에 **반드시 검토**되어야 합니다.

### A. 개인정보 보호법 (PIPA Compliance)
1.  **원칙:** 모든 민감 정보는 수집 즉시 익명화/가명화 처리합니다. 원본 데이터를 DB에 보관하는 것은 '최후의 수단'으로만 제한해야 합니다.
2.  **IP 주소 처리:** `sourceIpAnon` 필드에서 전체 IP를 저장하지 않고, 분석에 필요한 최소한의 정보(예: 지역 코드 또는 앞 3옥텟)만을 추출하여 마스킹합니다. (예: `192.x.y.z` $\rightarrow$ `192.0.0.0`)
3.  **사용자 ID 처리:** 사용자 로그인을 통한 추적이 필요할 경우, 내부 시스템에서 생성한 UUID 기반의 `pseudoUserId`만을 사용하고, 실제 계정 ID와는 분리하여 저장합니다 (Salted/Hashed).

### B. 보안 강화 로직
1.  **Rate Limiting & Throttling:** Gateway 레벨에서 동일 IP 또는 `pseudoUserId`의 트래킹 시도에 대해 초당 최대 호출 횟수를 제한해야 합니다. (봇 공격 및 과부하 방지)
2.  **Input Validation:** 모든 입력 데이터(특히 문자열 필드)는 XSS/SQL Injection 공격을 막기 위해 반드시 서버 측에서 이스케이프 처리하고 유효성 검사합니다.

## 5. 기술적 구현 체크리스트 (Self-Verification List)

| 항목 | 상태 | 조치 사항 및 이유 |
| :--- | :--- | :--- |
| **데이터 무결성** | ✅ | `listingId`와 `actionType`의 조합을 기준으로 이벤트가 중복 기록되지 않도록 Idempotency Key를 설계에 포함해야 합니다. |
| **확장성** | ✅ | 로깅/트래킹은 쓰기(Write)만 하는 비즈니스입니다. 따라서 동기적 DB 호출 대신 Kafka와 같은 메시지 큐를 사용해 병목 현상을 원천적으로 방지합니다. |
| **오류 처리** | 🔧 | Ingestion Service에서 데이터를 파싱하거나 마스킹하는 과정 중 실패할 경우, 해당 이벤트는 Dead Letter Queue (DLQ)로 전송되어 수동 검토가 가능하도록 합니다. |

---
<create_file path="/Users/seopro/커넥트ai복사/connect-ai/src/arch/LeadTrackingService_DesignSpec.md"># Lead Event Tracking System (LTS) Design Specification

## 1. 목표 및 범위
이 문서는 매수자가 매물 페이지에서 '카카오톡 보내기'와 같은 핵심 리드 액션을 취했을 때, 해당 이벤트를 안정적이고 법률적으로 안전하게 추적하고 공인중개사에게 알리는 시스템 아키텍처를 정의합니다.

## 2. 기술 요구사항
*   **신뢰성:** 이벤트 유실률 최소화 (Kafka/Message Queue 사용).
*   **확장성:** 대규모 트래픽 분산을 위한 비동기 처리 필수.
*   **보안/법규 준수:** 개인정보보호법(PIPA)을 최우선으로 준수하며, 모든 데이터는 수집 단계에서 가명화되어야 함.

## 3. 아키텍처 다이어그램 (High-Level Flow)
[Client] $\rightarrow$ [API Gateway] $\rightarrow$ [Ingestion Service] $\rightarrow$ [Kafka Topic: raw\_lead\_events] $\rightarrow$ { [DB Worker] & [Notification Service] }

### A. API Endpoint Specification
**Endpoint:** `POST /v1/leads/track`
**Response Code (Success):** `202 Accepted` (처리 예정)

**Request Body Schema (JSON)**
```json
{
  "listingId": "STRING", // 필수: 매물 고유 ID
  "timestampClient": "ISO8601 STRING", // 클라이언트 기록 시간 (UTC 권장)
  "actionType": "ENUM", // 예: KAKAOTALK_SEND, BOOKMARK_ADD 등
  "clientMetadata": {
    "pseudoUserId": "STRING", // 익명화된 사용자 UUID
    "sourceIpAnon": "STRING", // 마스킹된 IP 주소 (예: 192.0.0.0)
    "browserInfo": "STRING" // User Agent String
  }
}
```

### B. 핵심 처리 로직 (Ingestion Service Logic - Pseudocode Concept)
```python
def process_raw_lead_event(payload: dict):
    # 1. 유효성 검사 및 필터링
    if not is_valid(payload):
        raise InvalidPayloadError("필수 파라미터 누락")

    # 2. PIPA 준수 로직 (가명화) - 가장 중요!
    anon_ip = mask_ip(payload['clientMetadata']['sourceIpAnon']) # IP 마스킹 함수 호출
    pseudo_user_id = generate_or_lookup_uuid(payload['clientMetadata']['rawUserId']) # UUID 조회/생성

    # 3. 데이터 표준화 및 Enrichment (추가 정보 추가)
    enriched_data = {
        "listing_id": payload["listingId"],
        "pseudo_user_id": pseudo_user_id,
        "masked_ip": anon_ip,
        "action_type": payload["actionType"],
        # ... 기타 메타데이터
    }

    # 4. 이벤트 발행 (비동기)
    kafka_producer.publish(topic="raw_lead_events", message=enriched_data)
```

## 4. 보안 및 운영 체크리스트
*   [ ] **Rate Limiting:** IP/User 단위의 요청 제한을 반드시 구현해야 합니다.
*   [ ] **Logging:** 모든 트래킹 시도와 실패 케이스를 별도의 감사 로그(Audit Log)에 기록하고 모니터링해야 합니다.
*   [ ] **DLQ:** 메시지 큐에서 처리 실패한 이벤트는 DLQ로 격리하여, 주기적인 검토가 가능하도록 시스템화합니다.

</create_file>

✅ 코드를 통해 아키텍처 설계 명세서 파일(`/Users/seopro/커넥트ai복사/connect-ai/src/arch/LeadTrackingService_DesignSpec.md`)을 생성했습니다. 이 구조는 비동기 이벤트 기반이며, 법적 요구사항(PIPA)과 기술적 확장성(Kafka)을 모두 고려한 견고한 설계입니다.

📊 평가: 완료 — 요청하신 모든 기능(트래킹 로직, 아키텍처, API 명세, 보안 준수)이 구체적인 파일 형태로 정의되어 목표가 달성되었습니다.
📝 다음 단계: 이 명세서를 기반으로, 백엔드 게이트웨이에 해당 엔드포인트(`/v1/leads/track`)를 구현할 코드 스켈레톤을 작성해야 합니다. (예: FastAPI 또는 Express.js)

---
## 📁 파일 액션 결과

✅ 생성: ~/커넥트ai복사/connect-ai/src/arch/LeadTrackingService_DesignSpec.md
