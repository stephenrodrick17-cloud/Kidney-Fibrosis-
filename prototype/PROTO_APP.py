from __future__ import annotations

import os


os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

import streamlit as st

import PROTO_QUANTIFY as quantify
import PROTO_VALIDATE as validate

st.set_page_config(page_title="PROTO local research tool", layout="centered")
st.title("PROTO - local research tool")

warnings = validate.load_warnings()
for warning in warnings:
    st.warning(warning)

try:
    checkpoint_hash = validate.verify_checkpoint_hash()
except (OSError, ValueError) as error:
    st.error(f"Cannot start: {error}")
    st.stop()

st.caption("This page runs on this computer only. Results are saved below D:\\patent\\prototype\\.")
st.write(f"Frozen checkpoint check: passed ({checkpoint_hash})")

uploaded = st.file_uploader(
    "Choose one RGB kidney tissue image",
    type=["png", "jpg", "jpeg", "tif", "tiff"],
)
mpp = st.number_input(
    "Measured input micrometres per pixel",
    min_value=0.0,
    value=0.0,
    step=0.1,
    help="Enter the measured value. Zero means no value was supplied; the tool will not guess.",
)
output_subfolder = st.text_input("Output subfolder inside D:\\patent\\prototype", value="outputs")
acknowledged = st.checkbox(
    "I have read all five warnings and acknowledge local research use only."
)

if st.button("Check image"):
    try:
        if uploaded is None:
            raise ValueError("Choose an image first.")
        if mpp <= 0:
            raise ValueError(
                "Micrometres per pixel is required. Enter the measured value; the tool will not guess."
            )
        assessment = validate.validate_image(
            uploaded.getvalue(), float(mpp), uploaded.name
        )
        st.subheader(f"Validation status: {assessment.status}")
        st.json(validate.assessment_report(assessment))
    except (OSError, ValueError) as error:
        st.error(f"REFUSED: {error}")

if st.button("Run local measurement"):
    if not acknowledged:
        st.error("Read all five warnings and check the acknowledgement box first.")
    elif uploaded is None:
        st.error("Choose an image first.")
    elif mpp <= 0:
        st.error("Micrometres per pixel is required; the tool will not guess.")
    else:
        try:
            report, _ = quantify.run_quantification_data(
                uploaded.getvalue(),
                float(mpp),
                output_subfolder,
                source_name=uploaded.name,
            )
            st.subheader(f"Validation status: {report['validation_status']}")
            st.json(report)
            st.success("The report and images were saved locally.")
        except (OSError, ValueError, RuntimeError, TimeoutError) as error:
            st.error(f"Run stopped: {error}")
