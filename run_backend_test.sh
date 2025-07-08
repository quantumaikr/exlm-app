#!/bin/bash
# Run backend API test with virtual environment

cd backend
source venv/bin/activate
cd ..
python test_results/api_function_test.py