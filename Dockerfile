FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SERVE_STATIC=1 HF_HOME=/home/app/.cache/huggingface
WORKDIR /app
COPY requirements.txt requirements-production.txt ./
RUN python -m pip install --no-cache-dir -r requirements-production.txt
# CPU-only sentiment artifacts are cached separately from the GPU conversation service.
RUN python -m pip install --no-cache-dir 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu
COPY requirements-sentiment.txt ./
RUN python -m pip install --no-cache-dir -r requirements-sentiment.txt
RUN useradd --create-home app
COPY --chown=app:app . .
RUN python manage.py collectstatic --noinput && mkdir -p /home/app/.cache/huggingface && chown -R app:app /home/app/.cache
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "60", "--access-logfile", "-"]
