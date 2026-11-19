FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8501
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd --create-home --uid 1000 app
COPY --chown=app:app . .
USER app
EXPOSE 8501
CMD ["sh", "-c", "streamlit run dashboard/app.py --server.port ${PORT} --server.address 0.0.0.0"]
