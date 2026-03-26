import json
import base64
import io
import os
import sys

# Add parent directory to path for Vercel
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUMMARY_PROMPT = """
당신은 경제·시사 뉴스레터 전문 에디터입니다.

━━ 특수 이미지 처리 (최우선 적용) ━━
이미지에 "오늘의 뉴스 이것만 확인하자" 또는 "오늘 뉴스 이것만 확인하자" 라는 제목이 보이면:
- 반드시 아래 형식으로만 출력하고 다른 내용 절대 추가 금지:
[SPECIAL_SUMMARY]
(이미지에 보이는 텍스트를 OCR로 그대로 전부 추출 — 수정·요약 없이 원문 그대로)
[/SPECIAL_SUMMARY]

이미지에 날씨 정보(기온, 날씨 아이콘, 예보, 강수확률 등)가 주요 내용으로 보이면:
- 반드시 아래 형식으로만 출력하고 다른 내용 절대 추가 금지:
[WEATHER_SUMMARY]
(날씨 핵심 요약 — 오늘 날씨 + 기온 + 주요 특이사항, 2줄 이내 한국어)
[/WEATHER_SUMMARY]

━━ 일반 이미지 처리 ━━
위 특수 제목이 없는 경우, 아래 규칙을 따르세요.

⛔ 절대 금지:
- 이미지에 없는 기사를 추가하거나 내용을 지어내는 것 금지
- 이미지에 없는 기사 번호를 만들어내는 것 금지
- 목차 항목을 긴 문장으로 작성하는 것 금지 (7단어 이내 한 줄만)
- 목차 숫자가 이미지 실제 기사 수를 초과하는 것 금지

✅ 필수 규칙:
- 이미지에 보이는 기사 수 = 목차 항목 수 = 본문 기사 수 (반드시 일치)
- 목차: 번호 + [분야] + 7단어 이내 핵심 키워드만 (한 줄)
- 본문: ①핵심 ②포인트 ③시사점 각각 구체적 수치·인물·기관 포함 완전한 한 문장
- 날짜: 이미지에서 추출, 없으면 오늘 날짜 사용
- 분야 태그: [정치][경제][금융][증권][기업][국제][생활][기술]+/세부

[출력 형식]

<YYYY년 M월D일 뉴스>

1. [분야] 핵심키워드 요약 (한 줄)
2. [분야] 핵심키워드 요약 (한 줄)
(이미지 속 기사 수만큼만 작성)

▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔

1. [분야] 목차와 동일한 제목
①핵심: 실제 수치·인물·기관·날짜 포함 완전한 한 문장.
②포인트: 구체적 데이터·퍼센트·금액 근거로 한 문장.
③시사점: 투자·생활 직결 인사이트 한 문장.
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔

(이상 형식으로 이미지 속 모든 기사 반복)
"""


def handler(request):
    """Vercel Python Serverless Function"""
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }

    if request.method == "OPTIONS":
        return ("", 200, headers)

    if request.method != "POST":
        return (json.dumps({"error": "POST only"}), 405, headers)

    try:
        import google.generativeai as genai
        import PIL.Image

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return (json.dumps({"error": "GEMINI_API_KEY 환경변수가 설정되지 않았습니다."}), 400, headers)

        # 파일 업로드 처리
        if request.content_type and "multipart" in request.content_type:
            file = request.files.get("file")
            if not file:
                return (json.dumps({"error": "파일이 없습니다."}), 400, headers)
            img = PIL.Image.open(file.stream)
        else:
            data = request.get_json() or {}
            b64 = data.get("image_b64", "")
            if not b64:
                return (json.dumps({"error": "이미지가 없습니다."}), 400, headers)
            img_bytes = base64.b64decode(b64)
            img = PIL.Image.open(io.BytesIO(img_bytes))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content([SUMMARY_PROMPT, img])
        text = response.text.strip()

        return (json.dumps({"result": text}, ensure_ascii=False), 200, headers)

    except Exception as e:
        return (json.dumps({"error": str(e)}, ensure_ascii=False), 500, headers)
