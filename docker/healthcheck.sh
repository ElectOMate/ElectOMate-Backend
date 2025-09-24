#!/bin/bash
set -e

# Health check for ElectOMate Backend
curl -f http://localhost:8000/health || exit 1