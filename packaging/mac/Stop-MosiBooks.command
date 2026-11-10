#!/bin/bash
pkill -f "bookforge.cli serve" && echo "MosiBooks stopped." || echo "MosiBooks was not running."
sleep 1
