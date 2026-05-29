# AI City Master Plan - 진실의 원천

## 🏗️ 도시 개요
- **도시 이름:** 초자동화 영상 생산 도시 (Automated Video Production City)
- **핵심 기술 스택:** React + FastAPI, Gemini 3 & Veo 3.1 통합
- **운영 철학:** 지진(에러)은 데이터 불확실성, 자재는 데이터의 정확성, 지하 발전소(Backend)는 안정적인 API, 지상 랜드마크(Frontend)는 직관적인 사용자 경험 제공.

## ⚙️ 현재 공사 상황 (Protocol 0: Groundbreaking)
- **사용 모델:** Gemini 3, Veo 3.1 통합 시스템 설계 중.
- **데이터 파이프라인 상태:** 초기 스키마 정의 단계.
- **보안 점검:** `.env` 파일에 `GCP_API_KEY`와 `GCP_PROJECT_ID` 존재 여부 확인 필요 (현재 미확인).

## 📋 공사 진행 로그 (Build Log)
*초기 설계 완료. 다음 단계는 지하 발전소(FastAPI Backend)의 심장 구축입니다.*

---

<create_file path="AI_City_Project/.env"># 구글 발전소 출입증 (GCP Key)

GCP_API_KEY=YOUR_GCP_API_KEY_HERE
GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID_HERE
# 기타 환경 변수 추가 예정...

<create_file path="AI_City_Project/backend/main.py">from fastapi import FastAPI
from .services.google_ai import run_video_generation # Placeholder for the core logic

app = FastAPI(title="Video Generation Gateway")

@app.post("/generate")
async def generate_video(prompt: str, asset_id: str):
    """
    지상(React)의 요청을 받아 지하 발전소(AI Service)를 통해 영상 생성을 시작합니다.
    """
    print(f"🚀 [Main]: 요청 수신 - 프롬프트: {prompt}, 자재 ID: {asset_id}")
    # TODO: 실제 Veo/Gemini 호출 로직 구현 (다음 단계에서 채워질 예정)
    return {"status": "Processing", "message": "영상 생성이 시작되었습니다. 잠시 후 결과를 확인하세요."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

<create_file path="AI_City_Project/backend/services/google_ai.py">from vertexai.generative_models import GenerativeModel
import vertexai
from vertexai.vision_models import ImageGenerationModel
from vertexai.vision_models import VideoGenerationModel # Hypothetical Veo integration

# Vertex AI 초기화 (실제 환경에서는 인증 필요)
try:
    vertexai.init(project="YOUR_GCP_PROJECT_ID", location="us-central1")
except Exception as e:
    print(f"❌ [Error]: Vertex AI 초기화 실패. API 키 또는 프로젝트 ID를 확인하세요. 에러: {e}")

# 모델 및 도구 로드 (가상의 설정)
gemini_model = GenerativeModel("gemini-3-pro")
image_model = ImageGenerationModel("gemini-3-pro-image-preview")
video_model = VideoGenerationModel("veo-3.1-generate-preview")

def run_video_generation(prompt: str, asset_id: str):
    """
    Blueprint에 따른 4단계 공정 (Market Research -> Asset Factory -> Synthesis Lab -> Broadcasting)을 순차 실행합니다.
    """
    print("🛠️ [Service]: 영상 생성 파이프라인 시작!")

    # Zone 1 & 2: 시장 조사 및 자재 준비 (Gemini-3-Flash/Pro Image)
    # TODO: 실제 구글 검색 및 이미지 생성을 위한 로직 구현 필요.
    print(f"🔍 [Step 1/4]: 시장 조사 및 자재 준비 실행 중...")

    # Zone 3: 합성 연구소 (Gemini-3-Pro Image)
    # TODO: 사용자 캐릭터와 제품 합성 로직 구현 필요.
    print(f"🔬 [Step 2/4]: 합성 연구소 실행 중...")

    # Zone 4: 방송국 (Veo 3.1 Generate)
    # TODO: 실제 Veo 영상 생성을 위한 Polling 및 다운로드 로직 구현 필요.
    print(f"📺 [Step 3/4]: 방송국 송출 시작... (시간 소요 예정)")

    return {"status": "Success", "video_id": f"vid_{hash(prompt)}"}

# 이 파일은 나중에 Polling 및 Retry 로직이 추가될 것입니다.
print("✅ AI 터빈 서비스 모듈 로드 완료.")