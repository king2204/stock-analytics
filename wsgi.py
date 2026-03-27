# WSGI entry point for Elastic Beanstalk
import subprocess
import sys

def application(environ, start_response):
    """WSGI app for running Streamlit on EB"""
    status = "200 OK"
    response_headers = [("Content-Type", "text/plain")]
    start_response(status, response_headers)
    return [b"Streamlit app is running"]
