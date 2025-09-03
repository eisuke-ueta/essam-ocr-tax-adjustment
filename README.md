# essam-ocr-tax-adjustment

Tax Adjustment Document OCR Processing System - Extracts structured data from Japanese tax adjustment related documents including insurance deduction certificates, medical receipts, and donation receipts using AI models.

## Overview

This system automatically identifies and processes 6 types of Japanese tax adjustment documents:
0. **判定不能** (Undetermined/Unidentifiable)
1. **生命保険控除証明書** (Life Insurance Deduction Certificate)
2. **地震保険控除証明書** (Earthquake Insurance Deduction Certificate)  
3. **社会保険控除証明書** (Social Insurance Deduction Certificate)
4. **小規模共済控除証明書** (Small Mutual Aid Deduction Certificate)

The system provides two execution modes:
- **Local batch processing** using Google Gemini 2.5 Flash (`main.py`)
- **AWS Lambda API deployment** using Google Gemini 2.5 Flash (`lambda_function.py`)

## Setup

### Environment Variables
```bash
export GEMINI_API_KEY="your-gemini-api-key"  # For main.py (direct Gemini API)
export VERTEX_AI_PROJECT_ID="your-gcp-project-id"  # For lambda_function.py (Vertex AI)
export VERTEX_AI_LOCATION="asia-northeast1"  # For lambda_function.py (Vertex AI region)
export API_KEY="your-bearer-token"  # For lambda_function.py authentication
```

### Dependencies
```bash
pip install -r requirements.txt
```

## How To Run

### Local Batch Processing
```bash
python main.py
# Processes all files in data_error/ directory by default
# Outputs results as JSON with pprint display
```

**Directory Configuration**: The local script processes files from the directory specified in the `filepaths = glob.glob(f"data_error/*", recursive=False)` line in `main.py`. You can modify this to process files from any directory:
- `data_sample/` - Contains sample documents for testing
- `data_error/` - Currently configured directory for processing
- `data_error_1/` - Additional test documents

### API Testing
```bash
# Test deployed Lambda endpoint (production) - requires API key
python test_lambda_endpoint.py <FUNCTION_URL> data_sample/sample1.jpg <API_KEY>
```

## AI Models Used

- **Local Processing (main.py)**: Google Gemini 2.5 Flash via direct API
- **Lambda Processing (lambda_function.py)**: Google Gemini 2.5 Flash via Vertex AI

## Architecture

### Local Processing Flow
1. Reads files from the configured directory (currently `data_error/` in main.py)
2. First identifies certificate type using `prompt_certificate_type.txt`
3. Then extracts specific data using appropriate prompt based on certificate type
4. Outputs results as formatted JSON with certificate-specific fields

### API Processing Flow
1. Validates Bearer token authentication against configured API key
2. Receives base64-encoded file via REST API
3. First identifies certificate type using `prompt_certificate_type.txt`
4. Then extracts specific data using appropriate prompt based on certificate type
5. Returns structured JSON response with certificate-specific fields

## Testing

### 1. Test with the endpoint script (Recommended):
```bash
python test_lambda_endpoint.py <FUNCTION_URL> data_sample/sample1.jpg <API_KEY>
```

### 2. Test with curl:
```bash
# First, encode your file to base64
FILE_DATA=$(base64 -i data_sample/sample1.jpg)

# Then send request with Bearer token
curl -X POST "https://your-function-url.lambda-url.ap-northeast-1.on.aws/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d "{
    \"data\": \"$FILE_DATA\",
    \"media_type\": \"image/jpeg\"
  }"
```

### 3. Monitor deployment:
```bash
# View Lambda logs
aws logs tail /aws/lambda/essam-ocr-tax-return --follow --profile jinbay-dev

# Check function status
aws lambda get-function --function-name essam-ocr-tax-return --profile jinbay-dev
```

## Sample Data

The system includes sample tax adjustment documents in the `data_sample/` directory for testing:

- **社会保険控除証明書.png**, **社会保険控除証明書2.png** - Social insurance deduction certificate samples
- **小規模共済控除証明書.png**, **小規模共済控除証明書2.png**, **小規模共済控除証明書3.png** - Small mutual aid deduction certificate samples  
- **生命保険控除証明書.png**, **生命保険控除証明書2.png**, **生命保険控除証明書3.png** - Life insurance deduction certificate samples
- **地震保険控除証明書.png**, **地震保険控除証明書2.png**, **地震保険控除証明書3.png** - Earthquake insurance deduction certificate samples
- **複数.pdf** - Multi-page PDF sample with multiple document types

These samples can be used to test both local processing and the deployed API endpoint.

**Note**: The local batch processing script (`main.py`) currently processes files from the `data_error/` directory, but this can be easily modified to process any directory by changing the glob pattern in the main function.
## API Specification

### Endpoint
```
POST https://your-function-url.lambda-url.ap-northeast-1.on.aws/
```
- **Content-Type**: application/json
- **Authentication**: Bearer token required (API_KEY environment variable)

### Request Format
```json
{
  "data": "<base64-encoded-file-data>",
  "media_type": "<mime-type>"
}
```

**Headers:**
```
Authorization: Bearer <your-api-key>
Content-Type: application/json
```

### Response Format

The response structure varies based on the detected document type:

#### Common Response Structure
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "<certificate-type>",
      "Lifes": [<LifeInsuranceData>],
      "Earthquakes": [<EarthquakeInsuranceData>],
      "Socials": [<SocialInsuranceData>],
      "SmallMutuals": [<SmallMutualData>]
    }
  ]
}
```

#### Document Types
- `"0"` - Undetermined/Unidentifiable (判定不能)
- `"1"` - Life Insurance Deduction Certificate (生命保険控除証明書)
- `"2"` - Earthquake Insurance Deduction Certificate (地震保険控除証明書)
- `"3"` - Social Insurance Deduction Certificate (社会保険控除証明書)  
- `"4"` - Small Mutual Aid Deduction Certificate (小規模共済控除証明書)

#### Life Insurance Certificate Response (`"1"`)
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "1",
      "Lifes": [
        {
          "InsuranceClass": "1",
          "InsuranceCompanyName": {
            "Value": "△△生命保険株式会社",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "ContractNumber": {
            "Value": "123456789",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceType": {
            "Value": "終身",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "ContractDate": {
            "Value": "20200701",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsurancePeriod": {
            "Value": "終身",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceContractor": {
            "Value": "佐藤太郎",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceRecipient": {
            "Value": "佐藤花子",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "IsNewType": {
            "Value": "2:新",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "GeneralAmount": {
            "Value": 50000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "NursingCareAmount": {
            "Value": 15000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "PensionAmount": {
            "Value": 20000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "PensionPaymentDate": {
            "Value": "20240101",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          }
        }
      ],
      "Earthquakes": [],
      "Socials": [],
      "SmallMutuals": [],
    }
  ]
}
```

#### Earthquake Insurance Certificate Response (`"2"`)
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "2",
      "Lifes": [],
      "Earthquakes": [
        {
          "InsuranceCompanyName": {
            "Value": "東京海上日動火災保険株式会社",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "ContractNumber": {
            "Value": "123456789",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceType": {
            "Value": "地震保険",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "ContractStartDate": {
            "Value": "20000101",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "ContractEndDate": {
            "Value": "20301231",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsurancePeriod": {
            "Value": "30年",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceContractor": {
            "Value": "鈴木一郎",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "InsuranceProperty": {
            "Value": "建物及び家財",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "DeductionAmount": {
            "Value": 25000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "OldDeductionAmount": {
            "Value": 10000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "MaturityRefundAvailable": {
            "Value": "2",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          }
        }
      ],
      "Socials": [],
      "SmallMutuals": [],
    }
  ]
}
```

#### Social Insurance Certificate Response (`"3"`)
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "3",
      "Lifes": [],
      "Earthquakes": [],
      "Socials": [
        {
          "InsuranceType": {
            "Value": "国民年金",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "PaymentName": {
            "Value": "日本年金機構",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "PayerName": {
            "Value": "山田太郎",
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          },
          "Payment": {
            "Value": 72000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          }
        }
      ],
      "SmallMutuals": [],
    }
  ]
}
```

#### Small Mutual Aid Certificate Response (`"4"`)
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "4",
      "Lifes": [],
      "Earthquakes": [],
      "Socials": [],
      "SmallMutuals": [
        {
          "PremiumType": "3",
          "PremiumAmount": {
            "Value": 120000,
            "Position": {"Page": 1, "X": 0, "Y": 0, "Width": 0, "Height": 0}
          }
        }
      ],
    }
  ]
}
```

### Field Descriptions

#### Common Fields
- **Angle**: Rotation correction angle for image alignment (always 0 in current implementation)
- **Page**: Page number for PDF documents
- **CertificateType**: Type of detected document (書類の種類)

#### Life Insurance Fields (生命保険控除証明書)
- **InsuranceClass**: Insurance classification (保険区分) - "0:判定不能", "1:生命保険", "2:介護保険", "3:個人年金"
- **InsuranceCompanyName**: Insurance company name (保険会社名)
- **ContractNumber**: Insurance contract number (契約番号)
- **InsuranceType**: Insurance type (保険種類) - e.g., "終身"
- **ContractDate**: Insurance contract date (契約日) in yyyyMMdd format
- **InsurancePeriod**: Insurance period (保険期間) - e.g., "終身"  
- **InsuranceContractor**: Insurance contractor name (保険契約者名)
- **InsuranceRecipient**: Insurance recipient name (保険受取人名)
- **IsNewType**: New/Old system classification (新・旧制度区分) - "1:旧" or "2:新"
- **GeneralAmount**: General amount (証明額)
- **PensionPaymentDate**: Pension payment start date (年金支払開始日) in yyyyMMdd format

#### Earthquake Insurance Fields (地震保険控除証明書)
- **InsuranceCompanyName**: Insurance company name (保険会社名)
- **ContractNumber**: Insurance contract number (契約番号)
- **InsuranceType**: Insurance type (保険種類) - e.g., "地震保険"
- **ContractStartDate**: Insurance contract start date (契約開始日) in yyyyMMdd format
- **ContractEndDate**: Insurance contract end date (契約終了日) in yyyyMMdd format
- **InsurancePeriod**: Insurance period (保険期間) - e.g., "30年"
- **InsuranceContractor**: Insurance contractor name (保険契約者名)
- **InsuranceProperty**: Insurance property/object (保険対象物件) - e.g., "建物及び家財"
- **DeductionAmount**: Earthquake deduction amount (地震控除証明額)
- **OldDeductionAmount**: Old long-term deduction amount (旧長期控除証明額)
- **MaturityRefundAvailable**: Maturity refund availability (満期返戻金有無) - "0:判定不能", "1:あり", "2:なし"

#### Social Insurance Fields (社会保険控除証明書)
- **InsuranceType**: Insurance type (保険種類) - e.g., "国民年金"
- **PaymentName**: Payment destination name (保険料支払先名称) - e.g., "日本年金機構"
- **PayerName**: Payer name (保険料負担者氏名)
- **Payment**: Payment amount (保険料支払額)

#### Small Mutual Aid Fields (小規模共済控除証明書)
- **PremiumType**: Premium type (掛金の種類):
  - "0:判定不能" - Undetermined
  - "1:独立行政法人中小企業基盤整備機構の共済契約掛金" - SME Support Organization mutual aid
  - "2:企業型年金加入者掛金" - Corporate pension premium
  - "3:個人型年金加入者掛金" - Individual pension premium
  - "4:心身障害者扶養共済制度に関する契約の掛金" - Disability support mutual aid
- **PremiumAmount**: Premium amount (掛金)

**Notes**: 
- Fields that cannot be read will return `null`
- Position data currently returns placeholder coordinates (Page: 1, X/Y/Width/Height: 0)
- Gemini 2.5 Flash uses temperature=0 for consistent results
- Two-stage processing: first identifies document type, then extracts specific data
- Supports 6 types of Japanese tax adjustment documents
- All dates are standardized to yyyyMMdd format
- Array-based response structure with type-specific data sections
- PDF documents are processed page by page (max 20 pages)
- Multiple documents of the same type can be extracted from a single image/page

### Error Responses

#### 403 Forbidden - Missing Authorization
```json
{
  "error": "Authorization header is required"
}
```

#### 403 Forbidden - Invalid Authorization Format
```json
{
  "error": "Invalid authorization format. Use 'Bearer <token>'"
}
```

#### 403 Forbidden - Invalid API Key
```json
{
  "error": "Invalid API key"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Internal server error: <error details>"
}
```

## Deployment

### Quick Deployment
```bash
# Set your API key
export GEMINI_API_KEY="your-gemini-api-key"

# Run the automated deployment script
./deploy.sh
```

This will:
1. ✅ Create ECR repository
2. ✅ Build and push Docker image  
3. ✅ Create/update Lambda function
4. ✅ Create public Function URL
5. ✅ Display endpoint URL for testing

## Technical Details

### Certificate Detection and Processing

The system uses a two-stage processing approach:

1. **Document Type Detection**: Uses `prompt_certificate_type.txt` to identify which type of tax adjustment document is being processed (6 types supported)
2. **Specific Data Extraction**: Based on the detected type, uses the appropriate specialized prompt:
   - `prompt_life_insurance.txt` for life insurance certificates
   - `prompt_earthquake_insurance.txt` for earthquake insurance certificates
   - `prompt_social_insurance.txt` for social insurance certificates
   - `prompt_small_mutual_aid.txt` for small mutual aid certificates
   - `prompt_medical_expense.txt` for medical expense receipts
   - `prompt_donation_decuction.txt` for donation receipts

### Data Model Structure

The response follows a unified structure where each document type has its own array section:

#### Base Response Model
```json
{
  "Documents": [
    {
      "Angle": 0,
      "Page": 1,
      "CertificateType": "<detected-type>",
      "Lifes": [<LifeInsuranceData>],
      "Earthquakes": [<EarthquakeInsuranceData>], 
      "Socials": [<SocialInsuranceData>],
      "SmallMutuals": [<SmallMutualData>],
    }
  ]
}
```

#### Value-Position Model
Each extracted field follows this structure:
```json
{
  "Value": "<extracted-value>",
  "Position": {
    "Page": 1,
    "X": 0,
    "Y": 0,
    "Width": 0,
    "Height": 0
  }
}
```

### File Support
- **Images**: JPG, PNG (processed directly via Gemini)
- **PDFs**: Direct processing via Gemini's document endpoint (max 20 pages per PDF)
- **Language**: Optimized for Japanese tax adjustment documents (税務申告書類)

### AI Processing Details

The system uses Google Gemini 2.5 Flash with the following configuration:
- **Temperature**: 0 (for consistent results)
- **Max Output Tokens**: 6000
- **Response Format**: JSON
- **Top-k**: 20  
- **Top-p**: 0.95

#### Prompt Engineering
The system uses carefully crafted Japanese prompts that:
1. **Document Type Detection**: Identifies which of 6 document types is being processed
2. **Type-Specific Extraction**: Uses specialized prompts for each document type
3. **Provides few-shot examples**: For consistent formatting across different document layouts
4. **Handles various layouts**: Works with different document formats and designs
5. **Converts dates**: Automatically converts dates to yyyyMMdd format
6. **Returns null for unreadable fields**: Gracefully handles missing or unclear information
7. **Array-based output**: Returns multiple items when multiple documents of the same type are found
8. **Text normalization**: Removes unnecessary whitespace and formatting from extracted strings

#### Two-Stage Processing
1. **Stage 1**: Document type identification using `prompt_certificate_type.txt`
2. **Stage 2**: Detailed data extraction using type-specific prompts:
   - Life Insurance: Extracts 13 specific fields including insurance classification, contract details, amounts and dates
   - Earthquake Insurance: Extracts 11 fields including contract details, property information, and deduction amounts
   - Social Insurance: Extracts 4 fields including payer information
   - Small Mutual Aid: Extracts 2 fields including premium type and amount
   - Medical Expense: Extracts 6 fields including treatment details and amounts
   - Donation: Extracts 4 fields including donation details and amounts

### Error Handling
- Graceful handling of unreadable fields (returns null)
- JSON validation and cleanup
- Bearer token authentication validation
- Proper error responses with status codes:
  - 400: Invalid request (missing data)
  - 403: Authentication failed (missing/invalid Bearer token)
  - 500: Processing errors

## AWS Lambda Configuration

The Lambda function is configured with:
- **Runtime**: Python 3.11 with Docker container
- **Memory**: 256MB (configurable in deploy script)
- **Timeout**: 30 seconds (configurable in deploy script)
- **Architecture**: x86_64 (specified in Dockerfile)
- **Environment Variables**: 
  - `VERTEX_AI_PROJECT_ID`: Google Cloud Project ID for Vertex AI
  - `VERTEX_AI_LOCATION`: Vertex AI region (default: asia-northeast1)
  - `API_KEY`: Bearer token for authentication

### Container Image
The system uses a Docker container approach for deployment:
- Base image handles Python dependencies
- Includes all required libraries (google-genai, pypdf, etc.)
- Includes all prompt files for document type detection and extraction
- Optimized for cold start performance
- Supports PDF processing with page-by-page extraction