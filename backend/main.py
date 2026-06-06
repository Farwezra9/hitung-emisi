from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from pydantic import BaseModel
from typing import List, Optional

import pandas as pd
import pdfplumber
import io
import re

app = FastAPI(
    title="Carbon Emission Calculator API",
    version="1.0.0"
)

# ======================================================
# CORS CONFIGURATION
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# DATABASE FAKTOR EMISI (GHG PROTOCOL STANDARD)
# REFERENSI: IPCC 2006, GHG Protocol, ESDM RI, DEFRA
# ======================================================

FAKTOR_EMISI = {
    # ==================================================
    # SCOPE 1 - DIRECT EMISSION (Bahan Bakar & Gas)
    # ==================================================
    "premium": {
        "faktor": 2.31,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "pertalite": {
        "faktor": 2.31,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "pertamax": {
        "faktor": 2.31,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "solar": {
        "faktor": 2.68,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "bio_solar": {
        "faktor": 2.54,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "dexlite": {
        "faktor": 2.68,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "pertamina_dex": {
        "faktor": 2.68,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Fuel"
    },
    "lpg": {
        "faktor": 2.98,
        "satuan": "kg",
        "scope": "Scope 1 (Direct)",
        "kategori": "Gas"
    },
    "lng": {
        "faktor": 2.75,
        "satuan": "m3",
        "scope": "Scope 1 (Direct)",
        "kategori": "Gas"
    },
    "cng": {
        "faktor": 2.75,
        "satuan": "m3",
        "scope": "Scope 1 (Direct)",
        "kategori": "Gas"
    },
    "gas_alam": {
        "faktor": 2.75,
        "satuan": "m3",
        "scope": "Scope 1 (Direct)",
        "kategori": "Gas"
    },
    "genset_diesel": {
        "faktor": 2.68,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Generator"
    },
    "genset_bensin": {
        "faktor": 2.31,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Generator"
    },
    "batubara": {
        "faktor": 2.42,
        "satuan": "kg",
        "scope": "Scope 1 (Direct)",
        "kategori": "Industrial Fuel"
    },
    "pelumas": {
        "faktor": 2.90,
        "satuan": "liter",
        "scope": "Scope 1 (Direct)",
        "kategori": "Industrial"
    },

    # ==================================================
    # SCOPE 2 - ENERGY INDIRECT (Konsumsi Listrik)
    # ==================================================
    "listrik_pln": {
        "faktor": 0.85,
        "satuan": "kWh",
        "scope": "Scope 2 (Indirect - Energy)",
        "kategori": "Electricity"
    },
    "listrik_solar_panel": {
        "faktor": 0.05,
        "satuan": "kWh",
        "scope": "Scope 2 (Indirect - Energy)",
        "kategori": "Renewable Energy"
    },
    "listrik_hidro": {
        "faktor": 0.02,
        "satuan": "kWh",
        "scope": "Scope 2 (Indirect - Energy)",
        "kategori": "Renewable Energy"
    },
    "listrik_angin": {
        "faktor": 0.01,
        "satuan": "kWh",
        "scope": "Scope 2 (Indirect - Energy)",
        "kategori": "Renewable Energy"
    },

    # ==================================================
    # SCOPE 3 - VALUE CHAIN (Logistik, Sampah, Material)
    # ==================================================
    "pesawat_domestik": {
        "faktor": 0.12,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Transportation"
    },
    "pesawat_internasional": {
        "faktor": 0.15,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Transportation"
    },
    "kereta": {
        "faktor": 0.04,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Transportation"
    },
    "bus": {
        "faktor": 0.10,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Transportation"
    },
    "mobil_logistik": {
        "faktor": 0.21,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Logistics"
    },
    "truk_logistik": {
        "faktor": 0.27,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Logistics"
    },
    "kapal_logistik": {
        "faktor": 0.015,
        "satuan": "km",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Logistics"
    },
    "sampah_organik": {
        "faktor": 0.50,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Waste"
    },
    "sampah_anorganik": {
        "faktor": 0.20,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Waste"
    },
    "limbah_b3": {
        "faktor": 1.80,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Hazardous Waste"
    },
    "kertas": {
        "faktor": 1.30,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Office Material"
    },
    "plastik": {
        "faktor": 2.50,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Material"
    },
    "karton": {
        "faktor": 0.94,
        "satuan": "kg",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Packaging"
    },
    "air_bersih": {
        "faktor": 0.344,
        "satuan": "m3",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Water"
    },
    "air_limbah": {
        "faktor": 0.708,
        "satuan": "m3",
        "scope": "Scope 3 (Value Chain)",
        "kategori": "Wastewater"
    }
}

# ======================================================
# PYDANTIC MODEL INPUT
# ======================================================

class AktivitasInput(BaseModel):
    aktivitas: str
    detail_aktivitas: Optional[str] = ""
    periode: Optional[str] = ""
    jumlah: float

# ======================================================
# UTILITY FUNCTIONS
# ======================================================

def normalize_key(text: str) -> str:
    """Mengubah input string teks bebas menjadi format slug snake_case."""
    return (
        text.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )

def proses_perhitungan(data_inputs: list) -> dict:
    """Core function untuk menghitung emisi karbon (kg & Ton tCO2e)"""
    hasil_perhitungan = []

    summary = {
        "Scope 1 (Direct)": 0.0,
        "Scope 2 (Indirect - Energy)": 0.0,
        "Scope 3 (Value Chain)": 0.0
    }

    for item in data_inputs:
        key = normalize_key(item["aktivitas"])

        if key not in FAKTOR_EMISI:
            continue

        meta = FAKTOR_EMISI[key]
        jumlah = float(item["jumlah"])

        # Rumus utama standar internasional
        emisi_kg = jumlah * meta["faktor"]
        emisi_ton = emisi_kg / 1000

        summary[meta["scope"]] += emisi_ton

        hasil_perhitungan.append({
            "aktivitas": item["aktivitas"],
            "detail_aktivitas": item.get("detail_aktivitas", ""),
            "periode": item.get("periode", ""),
            "scope": meta["scope"],
            "kategori": meta["kategori"],
            "jumlah": jumlah,
            "satuan": meta["satuan"],
            "faktor_konversi": meta["faktor"],
            "emisi_kgCO2e": round(emisi_kg, 4),
            "emisi_tCO2e": round(emisi_ton, 4)
        })

    # Jika tidak ada aktivitas valid yang berhasil dihitung
    if not hasil_perhitungan:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada data aktivitas valid atau cocok dengan faktor emisi kami."
        )

    # Data penunjang grafik Recharts Frontend (Sudah dalam Ton tCO2e)
    chart_data = [
        {"name": "Scope 1", "value": round(summary["Scope 1 (Direct)"], 4), "color": "#EF4444", "deskripsi": "Bahan bakar langsung"},
        {"name": "Scope 2", "value": round(summary["Scope 2 (Indirect - Energy)"], 4), "color": "#EAB308", "deskripsi": "Konsumsi listrik"},
        {"name": "Scope 3", "value": round(summary["Scope 3 (Value Chain)"], 4), "color": "#3B82F6", "deskripsi": "Logistik & supply chain"}
    ]

    return {
        "total_tCO2e": round(sum(summary.values()), 4),
        "detail": hasil_perhitungan,
        "chartData": chart_data
    }

# ======================================================
# API ENDPOINTS
# ======================================================

@app.post("/api/hitung-emisi")
def hitung_emisi_endpoint(inputs: List[AktivitasInput]):
    """Endpoint untuk pemrosesan form manual dari frontend."""
    formatted_inputs = []

    for item in inputs:
        formatted_inputs.append({
            "aktivitas": item.aktivitas,
            "detail_aktivitas": item.detail_aktivitas,
            "periode": item.periode,
            "jumlah": item.jumlah
        })

    return proses_perhitungan(formatted_inputs)


@app.post("/api/import-file")
async def import_file(file: UploadFile = File(...)):
    """Endpoint untuk parser file Excel (.xlsx/.xls) dan dokumen PDF."""
    filename = file.filename.lower()
    extracted_rows = []

    # --------------------------------------------------
    # PARSER EXCEL
    # --------------------------------------------------
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))

        required_columns = [
            "Kategori Aktivitas",
            "Detail / Keterangan",
            "Jumlah"
        ]

        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Kolom '{col}' tidak ditemukan di berkas Excel. Gunakan template resmi."
                )

        for _, row in df.iterrows():
            if pd.isna(row["Kategori Aktivitas"]) or pd.isna(row["Jumlah"]):
                continue

            aktivitas_val = str(row["Kategori Aktivitas"]).strip()
            periode_val = ""
            
            if "Periode" in df.columns and pd.notna(row["Periode"]):
                if isinstance(row["Periode"], pd.Timestamp) or hasattr(row["Periode"], "strftime"):
                    periode_val = row["Periode"].strftime("%Y-%m-%d")
                else:
                    periode_str = str(row["Periode"]).strip()
                    periode_val = periode_str[:10] if len(periode_str) >= 10 else periode_str

            extracted_rows.append({
                "aktivitas": aktivitas_val,
                "detail_aktivitas": str(row["Detail / Keterangan"]) if pd.notna(row["Detail / Keterangan"]) else "",
                "periode": periode_val,
                "jumlah": float(row["Jumlah"])
            })

    # --------------------------------------------------
    # PARSER PDF (Dengan Proteksi Duplikasi Token)
    # --------------------------------------------------
    elif filename.endswith(".pdf"):
        content = await file.read()
        pdf = pdfplumber.open(io.BytesIO(content))
        all_text = ""

        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

        lines = all_text.split("\n")
        aktivitas_list = list(FAKTOR_EMISI.keys())

        for line in lines:
            if not line.strip():
                continue
                
            lower = line.lower()
            matched_key = None
            
            # Cari kecocokan kata kunci terpanjang terlebih dahulu (menghindari tumpang tindih token)
            sorted_aktivitas = sorted(aktivitas_list, key=len, reverse=True)
            for aktivitas in sorted_aktivitas:
                # Modifikasi regex agar mengenali kata utuh/snake_case pembatas ruang
                pattern = rf"\b{aktivitas.replace('_', '[_ ]')}\b"
                if re.search(pattern, lower) or aktivitas.replace("_", " ") in lower:
                    matched_key = aktivitas
                    break 

            if matched_key:
                angka = re.findall(r"\d+(?:[.,]\d+)?", line)
                if angka:
                    # Mengganti koma desimal lokal ke titik jika ada
                    num_str = angka[0].replace(",", ".")
                    try:
                        jumlah = float(num_str)
                    except ValueError:
                        jumlah = 1.0
                else:
                    jumlah = 1.0

                extracted_rows.append({
                    "aktivitas": matched_key,
                    "detail_aktivitas": line.strip(),
                    "periode": "", 
                    "jumlah": jumlah
                })

    else:
        raise HTTPException(
            status_code=400,
            detail="Format file tidak didukung. Gunakan .xlsx, .xls, atau .pdf"
        )

    return proses_perhitungan(extracted_rows)


@app.get("/api/faktor-emisi")
def get_faktor_emisi():
    """Mengembalikan daftar lengkap koefisien basis data emisi."""
    return FAKTOR_EMISI

# ======================================================
# RUN SERVICE
# ======================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )