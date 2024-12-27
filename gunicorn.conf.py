# gunicorn.conf.py
bind = "0.0.0.0:80"
workers = 2
wsgi_app = "run:app"  # points to your app factory in run.py