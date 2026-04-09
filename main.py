from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 🔍 BANK PARSER (Basic Logic)
# -----------------------------
def analyze_bank(file_path):
    with open(file_path, "r", errors="ignore") as f:
        text = f.read()

    credits = sum([float(x.replace(",", "")) for x in re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', text)])

    # rough assumption
    monthly_turnover = credits / 12
    net_income = monthly_turnover * 0.1  # 10% margin

    return {
        "monthly_turnover": monthly_turnover,
        "net_income": net_income
    }

# -----------------------------
# 📊 CIBIL ANALYZER
# -----------------------------
def analyze_cibil(file_path):
    with open(file_path, "r", errors="ignore") as f:
        text = f.read()

    score = 750
    if "794" in text:
        score = 794

    emi_matches = re.findall(r'EMI\s?:\s?₹?([\d,]+)', text)
    emis = [int(e.replace(",", "")) for e in emi_matches]

    total_emi = sum(emis)

    return {
        "cibil_score": score,
        "total_emi": total_emi
    }

# -----------------------------
# 🧠 SCORING ENGINE
# -----------------------------
def score_model(cibil, foir, balance_flag):
    score = 0

    # CIBIL
    if cibil > 750:
        score += 25
    elif cibil > 700:
        score += 15

    # FOIR
    if foir < 60:
        score += 25
    elif foir < 100:
        score += 10
    else:
        score -= 30

    # Liquidity
    if balance_flag:
        score -= 10

    return score

# -----------------------------
# ⚖️ DECISION ENGINE
# -----------------------------
def decision_logic(score, foir):
    if foir > 100:
        return "REJECT"
    elif score < 20:
        return "HIGH RISK - REFER"
    else:
        return "APPROVE"

# -----------------------------
# 📄 CAM GENERATOR
# -----------------------------
def generate_cam(data):
    file_path = "CAM_Report.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(file_path)

    table = Table([
        ["Metric", "Value"],
        ["CIBIL", data["cibil"]],
        ["Monthly Income", f"₹{int(data['income'])}"],
        ["Total EMI", f"₹{data['emi']}"],
        ["FOIR", f"{data['foir']:.2f}%"],
        ["Score", data["score"]],
        ["Decision", data["decision"]],
    ])

    content = [
        Paragraph("BERYL CREDIT APPRAISAL MEMORANDUM", styles['Title']),
        Spacer(1, 20),
        table
    ]

    doc.build(content)
    return file_path

# -----------------------------
# 🚀 MAIN API
# -----------------------------
@app.post("/underwrite/")
async def underwrite(bank: UploadFile = File(...), cibil: UploadFile = File(...)):

    # Save files
    with open(bank.filename, "wb") as f:
        shutil.copyfileobj(bank.file, f)

    with open(cibil.filename, "wb") as f:
        shutil.copyfileobj(cibil.file, f)

    # Analyze
    bank_data = analyze_bank(bank.filename)
    cibil_data = analyze_cibil(cibil.filename)

    total_emi = cibil_data["total_emi"]
    income = bank_data["net_income"]

    foir = (total_emi / income) * 100 if income > 0 else 999

    # Flags
    balance_flag = True if income < 50000 else False

    # Score
    score = score_model(cibil_data["cibil_score"], foir, balance_flag)

    # Decision
    decision = decision_logic(score, foir)

    # CAM
    pdf = generate_cam({
        "cibil": cibil_data["cibil_score"],
        "income": income,
        "emi": total_emi,
        "foir": foir,
        "score": score,
        "decision": decision
    })

    return FileResponse(pdf, filename="CAM_Report.pdf")