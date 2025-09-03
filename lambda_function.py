import json
import os
import random
import base64
from google import genai
from google.genai import types
import time
import pypdf
import tempfile

VERTEX_AI_PROJECT_ID = os.environ.get("VERTEX_AI_PROJECT_ID")
VERTEX_AI_LOCATION = os.environ.get("VERTEX_AI_LOCATION", "asia-northeast1")
API_KEY = os.environ.get("API_KEY")
client = genai.Client(
    vertexai=True, project=VERTEX_AI_PROJECT_ID, location=VERTEX_AI_LOCATION
)
VERTEX_AI_REGIONS = [
    "asia-northeast1",  # Tokyo
    "us-central1",  # Iowa
    "us-east1",  # South Carolina
    "us-east4",  # Northern Virginia
    "us-west1",  # Oregon
    "asia-northeast3",  # Seoul
    "asia-southeast1",  # Singapore
    "europe-west1",  # Belgium
    "europe-west2",  # London
    "europe-west4",  # Netherlands
    "global"
]
available_regions = VERTEX_AI_REGIONS.copy()
current_region_index = 0

def __switch_to_next_region():
    global current_region_index
    current_region_index = (current_region_index + 1) % len(available_regions)
    current_region = available_regions[current_region_index]
    print(f"Switching to region: {current_region}")
    __initialize_vertex_client()

def __initialize_vertex_client():
    global current_region_index, client
    current_region = available_regions[current_region_index]
    client = genai.Client(vertexai=True, project=VERTEX_AI_PROJECT_ID, location=current_region)

def __execute_vertex_ai_with_retry(filepath: str, prompt: str, mime_type: str, max_retries: int = 3,
    ) -> list[dict]:
        """Execute with multi-region failover and exponential backoff"""
        global current_region_index

        # Phase 1: Try all regions
        for region_attempt in range(len(available_regions)):
            try:
                # リージョン間の負荷分散用遅延
                time.sleep(random.uniform(0.5, 1.0))

                result = execute_gemini(filepath, prompt, mime_type)
                if region_attempt > 0:
                    current_region_index = 0
                return result

            except Exception as e:
                if _is_error_429(e):
                    print(f"Region {available_regions[current_region_index]} quota exhausted, switching region")
                    __switch_to_next_region()
                    continue
                elif _is_error_503(e):
                    print(f"Region {available_regions[current_region_index]} service unavailable, switching region")
                    __switch_to_next_region()
                    continue
                else:
                    raise e

        # Phase 2: Exponential backoff across all regions if all failed with 429
        for retry in range(max_retries):
            delay = (2**retry) + random.uniform(0, 1)
            print(f"All regions exhausted, retry {retry + 1}/{max_retries} after {delay:.1f}s")
            __async_delay(delay)

            for region_attempt in range(len(available_regions)):
                try:
                    result = execute_gemini(filepath, prompt, mime_type)
                    current_region_index = 0
                    return result

                except Exception as e:
                    if not _is_error_429(e) and not _is_error_503(e):
                        raise e
                    __switch_to_next_region()

        # All retries exhausted
        raise Exception("All retries exhausted")


def _is_error_429(error: Exception) -> bool:
        return "429" in str(error) or "Resource exhausted" in str(error)

def _is_error_503(error: Exception) -> bool:
    return "503" in str(error) or "Service unavailable" in str(error) or "Candidates token count is None" in str(error)

def __async_delay(seconds: float):
    time.sleep(seconds)

def json_string_to_json(json_string) -> list[dict]:
    try:
        cleaned_json_string = (
            json_string.replace("```json", "").replace("```", "").strip()
        )
        python_dict = json.loads(cleaned_json_string)
        return python_dict
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []

def execute_gemini(filepath: str, prompt: str, mime_type: str) -> list[dict]:
    with open(filepath, "rb") as f:
        file_data = f.read()
        data = base64.b64encode(file_data).decode("utf-8")

    output = []

    # --- 固定プロンプト & 入力画像 ----------------------------------
    contents = types.Content(
        role="user",
        parts=[
            types.Part(text=prompt),
            types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type, data=base64.b64decode(data)
                )
            ),
        ]
    )

    # --- GenerationConfig ------------------------------------------
    cfg = types.GenerateContentConfig(
        temperature=0,
        max_output_tokens=10240,
        response_mime_type="application/json",
        candidate_count=1,
        top_k=1,
        top_p=0.0,
        seed=1234567890,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    # --- 推論 --------------------------------
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=cfg,
    )
    # --- レスポンスの処理 ------------------------------------------
    if response and response.candidates and len(response.candidates) > 0:
        candidate = response.candidates[0]
        if hasattr(candidate, "content") and candidate.content:
            text = candidate.content.parts[0].text if candidate.content.parts else None
            if text:
                output = json_string_to_json(text)
        elif hasattr(candidate, "text"):
            text = candidate.text
            output = json_string_to_json(text)
        else:
            print("No text content in candidate")
    else:
        print("No candidates in response")

    return output

def get_default_api_response():
    return {
        "Angle": 0,
        "Page": 0,
        "CertificateType": "0",
        "Lifes": [],
        "Earthquakes": [],
        "Socials": [],
        "SmallMutuals": [],
    }

def get_life_insurance_api_response(page: int, outputs: list[dict], certificate_type: str) -> list[dict]:
    lifes = []
    for output in outputs:
        lifes.append({
            "InsuranceClass": (
                str(output.get("保険区分"))
                if str(output.get("保険区分"))
                else None
            ),
            "InsuranceCompanyName": (
                {
                    "Value": output.get("保険会社名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険会社名")
                else None
            ),
            "ContractNumber": (
                {
                    "Value": output.get("契約番号"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("契約番号")
                else None
            ),
            "InsuranceType": (
                {
                    "Value": output.get("保険種類"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険種類")
                else None
            ),
            "ContractDate": (
                {
                    "Value": output.get("契約日"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("契約日")
                else None
            ),
            "InsurancePeriod": (
                {
                    "Value": output.get("保険期間"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険期間")
                else None
            ),
            "InsuranceContractor": (
                {
                    "Value": output.get("保険契約者名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険契約者名")
                else None
            ),
            "InsuranceRecipient": (
                {
                    "Value": output.get("保険受取人名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険受取人名")
                else None
            ),
            "IsNewType": (
                {
                    "Value": output.get("新・旧制度区分"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("新・旧制度区分")
                else None
            ),
            "GeneralAmount": (
                {
                    "Value": output.get("証明額"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("証明額") is not None
                else None
            ),
            "PensionPaymentDate": (
                {
                    "Value": output.get("年金支払開始日"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("年金支払開始日")
                else None
            ),
        })

    return {
        "Angle": 0,
        "Page": page,
        "CertificateType": certificate_type,
        "Lifes": lifes,
        "Earthquakes": [],
        "Socials": [],
        "SmallMutuals": [],
    }

def get_earthquake_insurance_api_response(page: int, outputs: list[dict], certificate_type: str) -> list[dict]:
    earthquakes = []
    for output in outputs:
        earthquakes.append({
            "InsuranceCompanyName": (
                {
                    "Value": output.get("保険会社名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険会社名")
                else None
            ),
            "ContractNumber": (
                {
                    "Value": output.get("契約番号"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("契約番号")
                else None
            ),
            "InsuranceType": (
                {
                    "Value": output.get("保険種類"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険種類")
                else None
            ),
            "ContractStartDate": (
                {
                    "Value": output.get("契約開始日"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("契約開始日")
                else None
            ),
            "ContractEndDate": (
                {
                    "Value": output.get("契約終了日"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("契約終了日")
                else None
            ),
            "InsurancePeriod": (
                {
                    "Value": output.get("保険期間"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険期間")
                else None
            ),
            "InsuranceContractor": (
                {
                    "Value": output.get("保険契約者名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険契約者名")
                else None
            ),
            "InsuranceProperty": (
                {
                    "Value": output.get("保険対象物件"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険対象物件")
                else None
            ),
            "DeductionAmount": (
                {
                    "Value": output.get("地震控除証明額"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("地震控除証明額") is not None
                else None
            ),
            "OldDeductionAmount": (
                {
                    "Value": output.get("旧長期控除証明額"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("旧長期控除証明額") is not None
                else None
            ),
            "MaturityRefundAvailable": (
                {
                    "Value": output.get("満期返戻金有無"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("満期返戻金有無")
                else None
            ),
        })
    return {
        "Angle": 0,
        "Page": page,
        "CertificateType": certificate_type,
        "Lifes": [],
        "Earthquakes": earthquakes,
        "Socials": [],
        "SmallMutuals": [],
    }

def get_social_insurance_api_response(page: int, outputs: list[dict], certificate_type: str) -> list[dict]:
    socials = []
    for output in outputs:
        socials.append({
            "InsuranceType": (
                {
                    "Value": output.get("保険種類"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険種類")
                else None
            ),
            "PaymentName": (
                {
                    "Value": output.get("保険料支払先名称"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険料支払先名称")
                else None
            ),
            "PayerName": (
                {
                    "Value": output.get("保険料負担者氏名"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険料負担者氏名")
                else None
            ),
            "Payment": (
                {
                    "Value": output.get("保険料支払額"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("保険料支払額") is not None
                else None
            ),
        })
    return {
        "Angle": 0,
        "Page": page,
        "CertificateType": certificate_type,
        "Lifes": [],
        "Earthquakes": [],
        "Socials": socials,
        "SmallMutuals": [],
    }

def get_small_mutual_aid_api_response(page: int, outputs: list[dict], certificate_type: str) -> list[dict]:
    small_mutual_aids = []
    for output in outputs:
        small_mutual_aids.append({
            "PremiumType": (
                str(output.get("掛金の種類"))
                if output.get("掛金の種類")
                else None
            ),
            "PremiumAmount": (
                {
                    "Value": output.get("掛金"),
                    "Position": {
                        "Page": page,
                        "X": 0,
                        "Y": 0,
                        "Width": 0,
                        "Height": 0,
                    },
                }
                if output.get("掛金") is not None
                else None
            ),
        })

    return {
        "Angle": 0,
        "Page": page,
        "CertificateType": certificate_type,
        "Lifes": [],
        "Earthquakes": [],
        "Socials": [],
        "SmallMutuals": small_mutual_aids,
    }

def execute_extraction(filepath: str, page: int, mime_type: str) -> dict:
    print(f"[EXTRACTING]: {os.path.basename(filepath)}...")
    start_time = time.time()

    with open("prompt_certificate_type.txt", "r", encoding="utf-8") as file:
        prompt_certificate_type = file.read()

    output = __execute_vertex_ai_with_retry(filepath, prompt_certificate_type, mime_type)

    certificate_type = output.get("帳票の種類")
    if certificate_type == "1": # 生命保険控除証明書
        with open("prompt_life_insurance.txt", "r", encoding="utf-8") as file:
            prompt = file.read()
        outputs = __execute_vertex_ai_with_retry(filepath, prompt, mime_type)
        api_response = get_life_insurance_api_response(page, outputs, certificate_type)

    elif certificate_type == "2": # 地震保険控除証明書
        with open("prompt_earthquake_insurance.txt", "r", encoding="utf-8") as file:
            prompt = file.read()
        output = __execute_vertex_ai_with_retry(filepath, prompt, mime_type)
        api_response = get_earthquake_insurance_api_response(page, output, certificate_type)
    elif certificate_type == "3": # 社会保険控除証明書
        with open("prompt_social_insurance.txt", "r", encoding="utf-8") as file:
            prompt = file.read()
        output = __execute_vertex_ai_with_retry(filepath, prompt, mime_type)
        api_response = get_social_insurance_api_response(page, output, certificate_type)
    elif certificate_type == "4": # 小規模共済控除証明書
        with open("prompt_small_mutual_aid.txt", "r", encoding="utf-8") as file:
            prompt = file.read()
        output = __execute_vertex_ai_with_retry(filepath, prompt, mime_type)
        api_response = get_small_mutual_aid_api_response(page, output, certificate_type)
    else: # 判別できない場合
        print(f"Unknown certificate type: {certificate_type}. Using default response.")
        api_response = get_default_api_response()

    elapsed = time.time() - start_time  
    print(f"Processed {os.path.basename(filepath)} in {elapsed:.2f} seconds.")
    return api_response

def lambda_handler(event, context):
    try:
        # Check Bearer token authentication
        headers = event.get("headers", {})
        authorization = headers.get("Authorization") or headers.get("authorization")
        
        if not authorization:
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps({"error": "Authorization header is required"}),
            }
        
        if not authorization.startswith("Bearer "):
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps({"error": "Invalid authorization format. Use 'Bearer <token>'"}),
            }
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        if token != API_KEY:
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps({"error": "Invalid API key"}),
            }
        
        body = json.loads(event["body"])
        data = body.get("data")  # image or pdf data in base64 format
        media_type = body.get("media_type").lower()  # image/jpeg, image/png, or application/pdf
        media_data = base64.b64decode(data)

        # Create temporary file to save the media data
        if media_type == "image/jpeg":
            file_extension = ".jpg"
        elif media_type == "image/png":
            file_extension = ".png"
        elif media_type == "application/pdf":
            file_extension = ".pdf"
        else:
            raise ValueError(f"Unsupported media type: {media_type}")

        temp_fd, filepath = tempfile.mkstemp(suffix=file_extension)
        
        try:
            # Save the media data to the temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(media_data)

            documents = []
            if media_type == "image/jpeg" or media_type == "image/png":
                document = execute_extraction(filepath, 1, media_type)
                documents.append(document)
            elif media_type == "application/pdf":
                with open(filepath, 'rb') as file:
                    pdf_reader = pypdf.PdfReader(file)
                    num_pages = len(pdf_reader.pages)

                    if num_pages >= 20:
                        raise ValueError(f"Too many pages ({num_pages}) in {filepath}. Please split the PDF into smaller files.")

                    for page_num in range(num_pages):
                        page = page_num + 1
                        new_pdf_writer = pypdf.PdfWriter()
                        new_pdf_writer.add_page(pdf_reader.pages[page_num])
                        temp_fd_page, temp_page_filepath = tempfile.mkstemp(suffix=f'_page_{page}.pdf')

                        try:
                            with os.fdopen(temp_fd_page, 'wb') as temp_file:
                                new_pdf_writer.write(temp_file)
                            document = execute_extraction(temp_page_filepath, page, media_type)
                            documents.append(document)
                        except Exception as e:
                            print(f"Error processing page {page} of {filepath}: {e}")
                            raise e
                        finally:
                            if os.path.exists(temp_page_filepath):
                                os.unlink(temp_page_filepath)

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps({ "Documents": documents }, ensure_ascii=False),
            }

        finally:
            # Clean up the main temporary file
            if os.path.exists(filepath):
                os.unlink(filepath)

    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
