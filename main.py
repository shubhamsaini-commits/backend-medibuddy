from fastapi import FastAPI, UploadFile, File , Form
from pydantic import BaseModel
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
import os

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load rules
with open("pgx_rules.json") as f:
    data = json.load(f)

rules = data["rules"]

# Extract unique drugs for dropdown
drug_list = sorted({rule["drug"] for rule in rules})
class AnalyzeRequest(BaseModel):
    selected_drug: str
    detected_genes: list[str]


@app.get("/drugs")
def get_drugs():
    return {"drugs": drug_list}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), selected_drugs: list[str] = Form(...)):

    # Save uploaded VCF
    contents = await file.read()
    with open("temp.vcf", "wb") as f:
        f.write(contents)

    # Parse VCF
    detected_variants = extract_genes_from_vcf("temp.vcf")

    # Extract only gene names for UI
    detected_genes = list({v["gene"] for v in detected_variants})

    results = []

    for drug in selected_drugs:

        result = {
            "drug": drug,
            "risk": "Safe",
            "recommendation": "Standard dosing recommended"
        }

        # Check rule matches
        for rule in rules:
            if rule["drug"] != drug:
                continue

            for variant in detected_variants:
                if rule["gene"] == variant["gene"] and variant["genotype"] != "0/0":
                    result = {
                        "drug": rule["drug"],
                        "risk": rule["risk"],
                        "recommendation": rule["recommendation"]
                    }
                    break
        if os.path.exists("temp.vcf"):
            os.remove("temp.vcf")

        results.append(result)

    return {
        "detected_genes": detected_genes,
        "results": results
    }


def extract_genes_from_vcf(vcf_path):
    detected = []

    with open(vcf_path, "r") as f:
        for line in f:

            line = line.strip()

            # skip empty lines
            if not line:
                continue

            # skip header
            if line.startswith("#"):
                continue

            columns = line.split()

            # ensure enough columns exist
            if len(columns) < 10:
                continue

            info = columns[7]
            genotype = columns[9].split(":")[0]

            gene = None
            for item in info.split(";"):
                if item.startswith("GENE="):
                    gene = item.split("=")[1]

            if gene:
                detected.append({
                    "gene": gene,
                    "genotype": genotype
                })

    return detected

