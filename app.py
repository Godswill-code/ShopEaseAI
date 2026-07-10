import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
import os
import re
import string

# ----------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------
st.set_page_config(
    page_title="ShopEaseAI",
    page_icon="🛒",
    layout="wide"
)

# ----------------------------------------------------
# CUSTOM UI CSS
# ----------------------------------------------------
st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
    }
    .title-text {
        font-size: 36px !important;
        font-weight: 700 !important;
        color: #2c3e50 !important;
        margin-bottom: 10px;
    }
    .section-card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 25px;
    }
    .sentiment-badge {
        padding: 6px 12px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        font-size: 16px;
    }
    .positive { background-color: #2ecc71; }
    .negative { background-color: #e74c3c; }
    .neutral { background-color: #f1c40f; }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="title-text">🛒 ShopEaseAI</div>', unsafe_allow_html=True)
st.write("Predict customer sentiment, identify key feedback drivers and explore business insights.")

# ----------------------------------------------------
# LOAD MODEL & VECTORIZER
# ----------------------------------------------------
MODEL_PATH = "models/best_sentiment_model.pkl"
VECTORIZER_PATH = "models/tfidf_vectorizer.pkl"

try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
except Exception as e:
    st.error(f"Unable to load model or vectorizer.\n\n{e}")
    st.stop()

# ----------------------------------------------------
# TEXT CLEANING
# ----------------------------------------------------
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text

driver_keywords = {
    "Delivery": ["delivery", "driver", "shipping", "parcel", "late", "delay", "arrived"],
    "Product Quality": ["quality", "broken", "damaged", "faulty", "poor", "defective"],
    "Price": ["price", "expensive", "cheap", "refund", "cost", "value"],
    "Customer Support": ["support", "service", "agent", "help", "response", "complaint"],
    "Website/App": ["website", "app", "checkout", "payment", "login", "order"]
}

def detect_driver(text):
    text = str(text).lower()
    for driver, keywords in driver_keywords.items():
        if any(word in text for word in keywords):
            return driver
    return "Other"

# ----------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------
page = st.sidebar.selectbox(
    "Navigation",
    ["Single Prediction", "Batch Prediction", "Dashboard"]
)

# ====================================================
# SINGLE PREDICTION
# ====================================================
if page == "Single Prediction":

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🔍 Predict Customer Sentiment")

    review = st.text_area("Enter Customer Review")

    if st.button("Predict"):
        if review.strip() == "":
            st.warning("Please enter a review.")
        else:
            cleaned = clean_text(review)
            review_vector = vectorizer.transform([cleaned])
            prediction = model.predict(review_vector)[0]
            driver = detect_driver(cleaned)

            badge_class = (
                "positive" if prediction == "Positive"
                else "negative" if prediction == "Negative"
                else "neutral"
            )

            st.markdown(
                f"<span class='sentiment-badge {badge_class}'>{prediction}</span>",
                unsafe_allow_html=True
            )

            st.info(f"Likely Feedback Driver: **{driver}**")

    st.markdown('</div>', unsafe_allow_html=True)

# ====================================================
# BATCH PREDICTION
# ====================================================
elif page == "Batch Prediction":

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📁 Upload CSV for Batch Prediction")

    uploaded = st.file_uploader("Upload CSV", type="csv")

    if uploaded is not None:
        df = pd.read_csv(uploaded)

        if "review" not in df.columns:
            st.error("CSV must contain a 'review' column.")
        else:
            df["clean_review"] = df["review"].apply(clean_text)
            review_vectors = vectorizer.transform(df["clean_review"])
            df["predicted_sentiment"] = model.predict(review_vectors)
            df["sentiment_driver"] = df["clean_review"].apply(detect_driver)

            st.success("Prediction completed.")
            st.dataframe(df.head())

            st.download_button(
                label="Download Predictions",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="sentiment_predictions.csv",
                mime="text/csv"
            )

    st.markdown('</div>', unsafe_allow_html=True)

# ====================================================
# DASHBOARD
# ====================================================
else:

    st.subheader("📊 Business Dashboard")

    DATA_PATH = "data/processed/shopease_with_predictions.csv"

    if not os.path.exists(DATA_PATH):
        st.warning("Prediction dataset not found.\n\nRun Batch Prediction first.")
    else:
        df = pd.read_csv(DATA_PATH)

        # Determine country column
        if "country_name" in df.columns:
            country_col = "country_name"
        elif "country" in df.columns:
            country_col = "country"
        else:
            country_col = None

        # -------------------------
        # METRICS
        # -------------------------
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        col1.metric("Total Reviews", len(df))

        if "rating" in df.columns:
            col2.metric("Average Rating", round(df["rating"].mean(), 2))
        else:
            col2.metric("Average Rating", "N/A")

        if country_col:
            col3.metric("Countries", df[country_col].nunique())
        else:
            col3.metric("Countries", "N/A")

        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------
        # SENTIMENT DISTRIBUTION
        # -------------------------
        if "predicted_sentiment" in df.columns:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("😊 Sentiment Distribution")

            fig = px.histogram(
                df,
                x="predicted_sentiment",
                color="predicted_sentiment",
                title="Sentiment Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------
        # PRODUCT CATEGORY INSIGHTS
        # -------------------------
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📦 Product Category Insights")

        if "product_category" in df.columns and "predicted_sentiment" in df.columns:

            category_summary = (
                df.groupby("product_category")["predicted_sentiment"]
                .value_counts(normalize=True)
                .rename("percentage")
                .mul(100)
                .reset_index()
            )

            fig_cat = px.bar(
                category_summary,
                x="product_category",
                y="percentage",
                color="predicted_sentiment",
                title="Sentiment Breakdown by Product Category",
                barmode="group",
                text=category_summary["percentage"].round(1).astype(str) + "%"
            )

            fig_cat.update_layout(
                xaxis_title="Product Category",
                yaxis_title="Percentage (%)",
                legend_title="Sentiment",
                height=500
            )

            st.plotly_chart(fig_cat, use_container_width=True)

            negative_df = df[df["predicted_sentiment"] == "Negative"]
            top_negative = (
                negative_df["product_category"]
                .value_counts()
                .head(5)
                .reset_index()
                .rename(columns={"index": "product_category", "product_category": "count"})
            )

            st.markdown("### 🚨 Top 5 Categories with Most Negative Feedback")
            st.table(top_negative)

        else:
            st.warning("Product category data not available.")

        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------
        # DRIVER INSIGHTS
        # -------------------------
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🧭 Feedback Driver Insights")

        if "sentiment_driver" not in df.columns:
            if "review" in df.columns:
                df["sentiment_driver"] = df["review"].apply(detect_driver)
            elif "clean_review" in df.columns:
                df["sentiment_driver"] = df["clean_review"].apply(detect_driver)

        fig3 = px.pie(
            df,
            names="sentiment_driver",
            title="Distribution of Feedback Drivers",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set3
        )

        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # -------------------------
        # RAW DATA
        # -------------------------
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📄 Full Dataset")
        st.dataframe(df)
        st.markdown('</div>', unsafe_allow_html=True)
