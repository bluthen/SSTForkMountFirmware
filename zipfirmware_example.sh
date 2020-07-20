#!/usr/bin/env bash
cd piside
zip -r ../ssteq25-firmware-v${VERSION}_full.zip client_main/dist server client_advanced_slew_limits/dist -x *.idea* */settings.json *.sqlite *cache* *simulation_files*

