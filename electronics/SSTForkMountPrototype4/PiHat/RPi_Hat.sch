EESchema Schematic File Version 2
LIBS:RPi_Hat-rescue
LIBS:power
LIBS:device
LIBS:transistors
LIBS:conn
LIBS:linear
LIBS:regul
LIBS:74xx
LIBS:cmos4000
LIBS:adc-dac
LIBS:memory
LIBS:xilinx
LIBS:microcontrollers
LIBS:dsp
LIBS:microchip
LIBS:analog_switches
LIBS:motorola
LIBS:texas
LIBS:intel
LIBS:audio
LIBS:interface
LIBS:digital-audio
LIBS:philips
LIBS:display
LIBS:cypress
LIBS:siliconi
LIBS:opto
LIBS:atmel
LIBS:contrib
LIBS:valves
LIBS:isadore_custom_components
LIBS:SSTForkMountPrototype2-cache
LIBS:relays
LIBS:switches
LIBS:RPi_Hat-cache
EELAYER 25 0
EELAYER END
$Descr USLetter 11000 8500
encoding utf-8
Sheet 1 2
Title "SSTEQ25"
Date "2018-08-18"
Rev "0.0.5"
Comp "StarSync Trackers"
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Sheet
S 750  850  1000 1000
U 5515D395
F0 "RPi_GPIO" 60
F1 "RPi_GPIO.sch" 60
$EndSheet
$Comp
L pololu_D24V22F5 U2
U 1 1 5B02F72B
P 8200 1150
F 0 "U2" V 8450 1350 60  0000 C CNN
F 1 "pololu_D24V22F5" V 8450 700 60  0000 C CNN
F 2 "isadore_custom_footprints:pololu_D24V22F5" H 7950 750 60  0001 C CNN
F 3 "" H 7950 750 60  0001 C CNN
	1    8200 1150
	0    -1   -1   0   
$EndComp
$Comp
L Teensy_3.1 U3
U 1 1 5B02F798
P 8600 4200
F 0 "U3" H 8600 4950 60  0000 C CNN
F 1 "Teensy_3.1" H 8650 5400 60  0000 C CNN
F 2 "custom_footprints:Teensy-3.1" H 8700 4200 60  0001 C CNN
F 3 "" H 8700 4200 60  0000 C CNN
	1    8600 4200
	1    0    0    -1  
$EndComp
$Comp
L RJ12 J1
U 1 1 5B02F815
P 5850 3150
F 0 "J1" H 6050 3650 50  0000 C CNN
F 1 "RJ12" H 5700 3650 50  0000 C CNN
F 2 "SparkFun-Connectors:RJ11-6" H 5850 3150 50  0001 C CNN
F 3 "" H 5850 3150 50  0001 C CNN
	1    5850 3150
	1    0    0    -1  
$EndComp
$Comp
L BARREL_JACK CON1
U 1 1 5B02F876
P 6200 1200
F 0 "CON1" H 6200 1450 50  0000 C CNN
F 1 "BARREL_JACK" H 6200 1000 50  0000 C CNN
F 2 "isadore_custom_footprints:POWER_JACK_PTH" H 6200 1200 50  0001 C CNN
F 3 "" H 6200 1200 50  0000 C CNN
	1    6200 1200
	1    0    0    -1  
$EndComp
NoConn ~ 6350 2750
NoConn ~ 6350 2850
NoConn ~ 5650 3600
Wire Wire Line
	6500 1200 6700 1200
Wire Wire Line
	6700 1200 6700 1350
Wire Wire Line
	6700 1300 6500 1300
$Comp
L GND #PWR01
U 1 1 5B02F971
P 6700 1350
F 0 "#PWR01" H 6700 1100 50  0001 C CNN
F 1 "GND" H 6700 1200 50  0000 C CNN
F 2 "" H 6700 1350 50  0001 C CNN
F 3 "" H 6700 1350 50  0001 C CNN
	1    6700 1350
	1    0    0    -1  
$EndComp
Connection ~ 6700 1300
$Comp
L +12V #PWR02
U 1 1 5B02F99B
P 7000 1100
F 0 "#PWR02" H 7000 950 50  0001 C CNN
F 1 "+12V" H 7000 1240 50  0000 C CNN
F 2 "" H 7000 1100 50  0001 C CNN
F 3 "" H 7000 1100 50  0001 C CNN
	1    7000 1100
	0    1    1    0   
$EndComp
Wire Wire Line
	6500 1100 7000 1100
$Comp
L PWR_FLAG #FLG03
U 1 1 5B02F9C0
P 6650 1050
F 0 "#FLG03" H 6650 1125 50  0001 C CNN
F 1 "PWR_FLAG" H 6650 1200 50  0000 C CNN
F 2 "" H 6650 1050 50  0001 C CNN
F 3 "" H 6650 1050 50  0001 C CNN
	1    6650 1050
	1    0    0    -1  
$EndComp
Wire Wire Line
	6650 1050 6650 1100
Connection ~ 6650 1100
$Comp
L +5V #PWR04
U 1 1 5B02FA11
P 8450 1700
F 0 "#PWR04" H 8450 1550 50  0001 C CNN
F 1 "+5V" H 8450 1840 50  0000 C CNN
F 2 "" H 8450 1700 50  0001 C CNN
F 3 "" H 8450 1700 50  0001 C CNN
	1    8450 1700
	0    1    1    0   
$EndComp
$Comp
L GND #PWR05
U 1 1 5B02FA49
P 8400 1900
F 0 "#PWR05" H 8400 1650 50  0001 C CNN
F 1 "GND" H 8400 1750 50  0000 C CNN
F 2 "" H 8400 1900 50  0001 C CNN
F 3 "" H 8400 1900 50  0001 C CNN
	1    8400 1900
	1    0    0    -1  
$EndComp
Wire Wire Line
	8400 1600 8400 1700
Wire Wire Line
	8400 1700 8450 1700
Wire Wire Line
	8300 1600 8300 1800
Wire Wire Line
	8300 1800 8400 1800
Wire Wire Line
	8400 1800 8400 1900
Wire Wire Line
	8200 1750 8200 1600
NoConn ~ 8100 1600
Text GLabel 7950 1700 0    60   Output ~ 0
PG
Wire Wire Line
	8000 1600 8000 1700
Wire Wire Line
	8000 1700 7950 1700
$Comp
L PWR_FLAG #FLG06
U 1 1 5B02FAC3
P 6750 1250
F 0 "#FLG06" H 6750 1325 50  0001 C CNN
F 1 "PWR_FLAG" H 6750 1400 50  0000 C CNN
F 2 "" H 6750 1250 50  0001 C CNN
F 3 "" H 6750 1250 50  0001 C CNN
	1    6750 1250
	0    1    1    0   
$EndComp
Wire Wire Line
	6750 1250 6700 1250
Connection ~ 6700 1250
Text GLabel 5850 3750 3    60   Output ~ 0
AG_RA-X
Text GLabel 5950 3750 3    60   Output ~ 0
AG_DEC-Y
Text GLabel 6050 3750 3    60   Output ~ 0
AG_DEC+Y
Text GLabel 6150 3750 3    60   Output ~ 0
AG_RA+X
$Comp
L GND #PWR07
U 1 1 5B02FBB0
P 5700 3750
F 0 "#PWR07" H 5700 3500 50  0001 C CNN
F 1 "GND" H 5700 3600 50  0000 C CNN
F 2 "" H 5700 3750 50  0001 C CNN
F 3 "" H 5700 3750 50  0001 C CNN
	1    5700 3750
	0    1    1    0   
$EndComp
Wire Wire Line
	5750 3600 5750 3750
Wire Wire Line
	5750 3750 5700 3750
Wire Wire Line
	5850 3600 5850 3750
Wire Wire Line
	5950 3600 5950 3750
Wire Wire Line
	6050 3600 6050 3750
Wire Wire Line
	6150 3600 6150 3750
Text GLabel 7450 4250 0    60   Input ~ 0
AG_RA+X
Text GLabel 7450 4100 0    60   Input ~ 0
AG_RA-X
Text GLabel 7450 3050 0    60   Input ~ 0
RPI_TX
Text GLabel 7450 3200 0    60   Output ~ 0
RPI_RX
Wire Wire Line
	7450 3200 7600 3200
Wire Wire Line
	7450 3050 7600 3050
Wire Wire Line
	7450 4100 7600 4100
Wire Wire Line
	7450 4250 7600 4250
Text GLabel 9700 4250 2    60   Input ~ 0
AG_DEC-Y
Text GLabel 9700 4400 2    60   Input ~ 0
AG_DEC+Y
Wire Wire Line
	9600 4250 9700 4250
Wire Wire Line
	9600 4400 9700 4400
Text GLabel 9700 4550 2    60   Input ~ 0
PG
Wire Wire Line
	9600 4550 9700 4550
$Comp
L +3V3 #PWR08
U 1 1 5B03015C
P 9700 3200
F 0 "#PWR08" H 9700 3050 50  0001 C CNN
F 1 "+3V3" H 9700 3340 50  0000 C CNN
F 2 "" H 9700 3200 50  0001 C CNN
F 3 "" H 9700 3200 50  0001 C CNN
	1    9700 3200
	0    1    1    0   
$EndComp
$Comp
L +5V #PWR09
U 1 1 5B030178
P 9700 2900
F 0 "#PWR09" H 9700 2750 50  0001 C CNN
F 1 "+5V" H 9700 3040 50  0000 C CNN
F 2 "" H 9700 2900 50  0001 C CNN
F 3 "" H 9700 2900 50  0001 C CNN
	1    9700 2900
	0    1    1    0   
$EndComp
NoConn ~ 9600 3050
Wire Wire Line
	9600 2900 9700 2900
Wire Wire Line
	9600 3200 9700 3200
Text GLabel 9700 4100 2    60   Output ~ 0
DEC_MS3
Text GLabel 9700 3950 2    60   Output ~ 0
DEC_MS2
Wire Wire Line
	9600 3950 9700 3950
Wire Wire Line
	9600 4100 9700 4100
Text GLabel 9700 3650 2    60   Output ~ 0
DEC_STEP
Text GLabel 9700 3800 2    60   Output ~ 0
DEC_MS1
Wire Wire Line
	9600 3650 9700 3650
Wire Wire Line
	9600 3800 9700 3800
Text GLabel 7500 3800 0    60   Output ~ 0
RA_MS2
Text GLabel 7500 3950 0    60   Output ~ 0
RA_MS1
Wire Wire Line
	7500 3800 7600 3800
Wire Wire Line
	7500 3950 7600 3950
$Comp
L GND #PWR010
U 1 1 5B03405D
P 7500 2900
F 0 "#PWR010" H 7500 2650 50  0001 C CNN
F 1 "GND" H 7500 2750 50  0000 C CNN
F 2 "" H 7500 2900 50  0001 C CNN
F 3 "" H 7500 2900 50  0001 C CNN
	1    7500 2900
	0    1    1    0   
$EndComp
Wire Wire Line
	7500 2900 7600 2900
Text GLabel 9750 3500 2    60   Output ~ 0
DEC_DIR
Text GLabel 7450 3500 0    60   Output ~ 0
RA_STEP
Text GLabel 7450 3650 0    60   Output ~ 0
RA_MS3
Wire Wire Line
	7450 3500 7600 3500
Wire Wire Line
	7450 3650 7600 3650
Wire Wire Line
	9600 3500 9750 3500
NoConn ~ 8350 2450
NoConn ~ 8500 2450
NoConn ~ 8700 2450
NoConn ~ 8850 2450
NoConn ~ 8350 5400
NoConn ~ 8500 5400
NoConn ~ 8650 5400
NoConn ~ 8800 5400
NoConn ~ 8950 5400
NoConn ~ 9600 4700
NoConn ~ 9600 4850
$Comp
L SparkFun_BigEasyDriver U4
U 1 1 5B6F4C8E
P 1750 5750
F 0 "U4" H 1500 6300 60  0000 C CNN
F 1 "SparkFun_BigEasyDriver" H 1750 5200 60  0000 C CNN
F 2 "custom_footprints:BED_PWR" V 2100 5600 60  0001 C CNN
F 3 "" V 2100 5600 60  0001 C CNN
	1    1750 5750
	1    0    0    -1  
$EndComp
$Comp
L SparkFun_BigEasyDriver U5
U 1 1 5B6F4E1B
P 1750 7200
F 0 "U5" H 1500 7750 60  0000 C CNN
F 1 "SparkFun_BigEasyDriver" H 1750 6650 60  0000 C CNN
F 2 "custom_footprints:BED_PWR" V 2100 7050 60  0001 C CNN
F 3 "" V 2100 7050 60  0001 C CNN
	1    1750 7200
	1    0    0    -1  
$EndComp
NoConn ~ 9600 3350
Text GLabel 7450 3350 0    60   Output ~ 0
RA_DIR
Wire Wire Line
	7450 3350 7600 3350
NoConn ~ 7600 4400
NoConn ~ 7600 4550
NoConn ~ 7600 4700
NoConn ~ 7600 4850
Text GLabel 2450 5200 2    60   Input ~ 0
RA_DIR
Text GLabel 2450 5350 2    60   Input ~ 0
RA_STEP
Text GLabel 2500 6100 2    60   Input ~ 0
RA_MS1
Text GLabel 2500 6000 2    60   Input ~ 0
RA_MS2
Text GLabel 2500 5900 2    60   Input ~ 0
RA_MS3
$Comp
L GND #PWR011
U 1 1 5B6F6057
P 2450 5500
F 0 "#PWR011" H 2450 5250 50  0001 C CNN
F 1 "GND" H 2450 5350 50  0000 C CNN
F 2 "" H 2450 5500 50  0001 C CNN
F 3 "" H 2450 5500 50  0001 C CNN
	1    2450 5500
	0    -1   -1   0   
$EndComp
$Comp
L +3.3V #PWR012
U 1 1 5B6F607D
P 2600 5600
F 0 "#PWR012" H 2600 5450 50  0001 C CNN
F 1 "+3.3V" H 2600 5740 50  0000 C CNN
F 2 "" H 2600 5600 50  0001 C CNN
F 3 "" H 2600 5600 50  0001 C CNN
	1    2600 5600
	0    1    1    0   
$EndComp
NoConn ~ 2300 5700
NoConn ~ 2300 5800
Wire Wire Line
	2300 5900 2500 5900
Wire Wire Line
	2300 6000 2500 6000
Wire Wire Line
	2300 6100 2500 6100
NoConn ~ 2300 6200
Wire Wire Line
	2300 5300 2350 5300
Wire Wire Line
	2350 5300 2350 5200
Wire Wire Line
	2350 5200 2450 5200
Wire Wire Line
	2300 5400 2400 5400
Wire Wire Line
	2400 5400 2400 5350
Wire Wire Line
	2400 5350 2450 5350
Wire Wire Line
	2300 5500 2450 5500
Wire Wire Line
	2300 5600 2600 5600
Text GLabel 2450 6700 2    60   Input ~ 0
DEC_DIR
Text GLabel 2450 6800 2    60   Input ~ 0
DEC_STEP
Text GLabel 2450 7350 2    60   Input ~ 0
DEC_MS3
Text GLabel 2450 7450 2    60   Input ~ 0
DEC_MS2
Text GLabel 2450 7550 2    60   Input ~ 0
DEC_MS1
NoConn ~ 2300 7650
NoConn ~ 2300 7250
NoConn ~ 2300 7150
$Comp
L +3.3V #PWR013
U 1 1 5B6F6486
P 2500 7050
F 0 "#PWR013" H 2500 6900 50  0001 C CNN
F 1 "+3.3V" H 2500 7190 50  0000 C CNN
F 2 "" H 2500 7050 50  0001 C CNN
F 3 "" H 2500 7050 50  0001 C CNN
	1    2500 7050
	0    1    1    0   
$EndComp
$Comp
L GND #PWR014
U 1 1 5B6F64AC
P 2400 6950
F 0 "#PWR014" H 2400 6700 50  0001 C CNN
F 1 "GND" H 2400 6800 50  0000 C CNN
F 2 "" H 2400 6950 50  0001 C CNN
F 3 "" H 2400 6950 50  0001 C CNN
	1    2400 6950
	0    -1   -1   0   
$EndComp
Wire Wire Line
	2300 6750 2400 6750
Wire Wire Line
	2400 6750 2400 6700
Wire Wire Line
	2400 6700 2450 6700
Wire Wire Line
	2300 6850 2400 6850
Wire Wire Line
	2400 6850 2400 6800
Wire Wire Line
	2400 6800 2450 6800
Wire Wire Line
	2300 6950 2400 6950
Wire Wire Line
	2300 7050 2500 7050
Wire Wire Line
	2300 7350 2450 7350
Wire Wire Line
	2300 7450 2450 7450
Wire Wire Line
	2300 7550 2450 7550
$Comp
L GND #PWR015
U 1 1 5B6F6879
P 1200 7050
F 0 "#PWR015" H 1200 6800 50  0001 C CNN
F 1 "GND" H 1200 6900 50  0000 C CNN
F 2 "" H 1200 7050 50  0001 C CNN
F 3 "" H 1200 7050 50  0001 C CNN
	1    1200 7050
	0    1    1    0   
$EndComp
$Comp
L GND #PWR016
U 1 1 5B6F68A8
P 1200 5600
F 0 "#PWR016" H 1200 5350 50  0001 C CNN
F 1 "GND" H 1200 5450 50  0000 C CNN
F 2 "" H 1200 5600 50  0001 C CNN
F 3 "" H 1200 5600 50  0001 C CNN
	1    1200 5600
	0    1    1    0   
$EndComp
Wire Wire Line
	1200 5600 1250 5600
Wire Wire Line
	1200 7050 1250 7050
$Comp
L D D1
U 1 1 5B6F83CF
P 3050 1850
F 0 "D1" H 3050 1950 50  0000 C CNN
F 1 "1N4001" H 3050 1750 50  0000 C CNN
F 2 "Diodes_ThroughHole:D_A-405_P7.62mm_Horizontal" H 3050 1850 50  0001 C CNN
F 3 "" H 3050 1850 50  0001 C CNN
	1    3050 1850
	-1   0    0    1   
$EndComp
$Comp
L D D2
U 1 1 5B6F843A
P 4550 1950
F 0 "D2" H 4550 2050 50  0000 C CNN
F 1 "1N4001" H 4550 1850 50  0000 C CNN
F 2 "Diodes_ThroughHole:D_A-405_P7.62mm_Horizontal" H 4550 1950 50  0001 C CNN
F 3 "" H 4550 1950 50  0001 C CNN
	1    4550 1950
	-1   0    0    1   
$EndComp
Wire Wire Line
	2400 1500 2750 1500
Wire Wire Line
	2700 1500 2700 1850
Wire Wire Line
	3200 1850 3400 1850
Wire Wire Line
	3400 1500 3400 2350
Wire Wire Line
	3350 1500 3450 1500
Wire Wire Line
	4100 1600 4250 1600
Wire Wire Line
	4200 1600 4200 1950
Wire Wire Line
	4200 1950 4400 1950
$Comp
L R R1
U 1 1 5B6F8613
P 2950 3100
F 0 "R1" V 3030 3100 50  0000 C CNN
F 1 "10k" V 2950 3100 50  0000 C CNN
F 2 "Resistors_ThroughHole:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal" V 2880 3100 50  0001 C CNN
F 3 "" H 2950 3100 50  0001 C CNN
	1    2950 3100
	0    1    1    0   
$EndComp
$Comp
L +12V #PWR017
U 1 1 5B6F8838
P 3400 1050
F 0 "#PWR017" H 3400 900 50  0001 C CNN
F 1 "+12V" H 3400 1190 50  0000 C CNN
F 2 "" H 3400 1050 50  0001 C CNN
F 3 "" H 3400 1050 50  0001 C CNN
	1    3400 1050
	1    0    0    -1  
$EndComp
Wire Wire Line
	2550 1100 2750 1100
$Comp
L +12V #PWR018
U 1 1 5B6F88D7
P 4150 1200
F 0 "#PWR018" H 4150 1050 50  0001 C CNN
F 1 "+12V" H 4150 1340 50  0000 C CNN
F 2 "" H 4150 1200 50  0001 C CNN
F 3 "" H 4150 1200 50  0001 C CNN
	1    4150 1200
	0    -1   -1   0   
$EndComp
Wire Wire Line
	4150 1200 4250 1200
$Comp
L SW_SPST SW1
U 1 1 5B6F8977
P 2300 2150
F 0 "SW1" H 2300 2275 50  0000 C CNN
F 1 "SW_SPST" H 2300 2050 50  0000 C CNN
F 2 "custom_footprints:PWR_SWITCH_RA1H1C112R" H 2300 2150 50  0001 C CNN
F 3 "" H 2300 2150 50  0001 C CNN
	1    2300 2150
	1    0    0    -1  
$EndComp
Wire Wire Line
	2700 1850 2900 1850
$Comp
L +12V #PWR019
U 1 1 5B6F90E6
P 2050 2150
F 0 "#PWR019" H 2050 2000 50  0001 C CNN
F 1 "+12V" H 2050 2290 50  0000 C CNN
F 2 "" H 2050 2150 50  0001 C CNN
F 3 "" H 2050 2150 50  0001 C CNN
	1    2050 2150
	0    -1   -1   0   
$EndComp
Wire Wire Line
	2050 2150 2100 2150
Wire Wire Line
	2500 2150 2700 2150
Connection ~ 2700 1500
$Comp
L GND #PWR020
U 1 1 5B6F92FB
P 2400 1500
F 0 "#PWR020" H 2400 1250 50  0001 C CNN
F 1 "GND" H 2400 1350 50  0000 C CNN
F 2 "" H 2400 1500 50  0001 C CNN
F 3 "" H 2400 1500 50  0001 C CNN
	1    2400 1500
	0    1    1    0   
$EndComp
Connection ~ 3400 1500
Wire Wire Line
	4900 1950 4700 1950
$Comp
L +12C #PWR021
U 1 1 5B6F96FF
P 2550 1100
F 0 "#PWR021" H 2550 950 50  0001 C CNN
F 1 "+12C" H 2550 1250 50  0000 C CNN
F 2 "" H 2550 1100 50  0001 C CNN
F 3 "" H 2550 1100 50  0001 C CNN
	1    2550 1100
	0    -1   -1   0   
$EndComp
$Comp
L +12C #PWR022
U 1 1 5B6F9731
P 4900 1150
F 0 "#PWR022" H 4900 1000 50  0001 C CNN
F 1 "+12C" H 4900 1300 50  0000 C CNN
F 2 "" H 4900 1150 50  0001 C CNN
F 3 "" H 4900 1150 50  0001 C CNN
	1    4900 1150
	1    0    0    -1  
$EndComp
Wire Wire Line
	3400 1100 3400 1050
Wire Wire Line
	4850 1200 4900 1200
Wire Wire Line
	4900 1200 4900 1150
Wire Wire Line
	4850 1600 4900 1600
$Comp
L +12V #PWR023
U 1 1 5B6FA55B
P 5000 1750
F 0 "#PWR023" H 5000 1600 50  0001 C CNN
F 1 "+12V" H 5000 1890 50  0000 C CNN
F 2 "" H 5000 1750 50  0001 C CNN
F 3 "" H 5000 1750 50  0001 C CNN
	1    5000 1750
	0    1    1    0   
$EndComp
Connection ~ 4200 1600
Text GLabel 4200 3100 2    60   Output ~ 0
PWR_SW_PI
Text GLabel 2900 2800 0    60   Input ~ 0
PWR_RELAY_PI
$Comp
L R R2
U 1 1 5B71C91C
P 3100 2800
F 0 "R2" V 3180 2800 50  0000 C CNN
F 1 "390" V 3100 2800 50  0000 C CNN
F 2 "Resistors_ThroughHole:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal" V 3030 2800 50  0001 C CNN
F 3 "" H 3100 2800 50  0001 C CNN
	1    3100 2800
	0    1    1    0   
$EndComp
Wire Wire Line
	2900 2800 2950 2800
Wire Wire Line
	3250 2800 3300 2800
$Comp
L LTV-827 U1
U 1 1 5B71CB47
P 3600 3100
F 0 "U1" H 3400 3500 50  0000 L CNN
F 1 "VOD223T" H 3600 3500 50  0000 L CNN
F 2 "Housings_SOIC:SOIC-8_3.9x4.9mm_Pitch1.27mm" H 3400 2750 50  0001 L CIN
F 3 "" H 3600 3000 50  0001 L CNN
	1    3600 3100
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR024
U 1 1 5B71CC2A
P 4000 3000
F 0 "#PWR024" H 4000 2750 50  0001 C CNN
F 1 "GND" H 4000 2850 50  0000 C CNN
F 2 "" H 4000 3000 50  0001 C CNN
F 3 "" H 4000 3000 50  0001 C CNN
	1    4000 3000
	0    -1   -1   0   
$EndComp
$Comp
L GND #PWR025
U 1 1 5B71CCAE
P 4000 3300
F 0 "#PWR025" H 4000 3050 50  0001 C CNN
F 1 "GND" H 4000 3150 50  0000 C CNN
F 2 "" H 4000 3300 50  0001 C CNN
F 3 "" H 4000 3300 50  0001 C CNN
	1    4000 3300
	0    -1   -1   0   
$EndComp
Wire Wire Line
	3900 3300 4000 3300
Wire Wire Line
	3900 3000 4000 3000
$Comp
L GND #PWR026
U 1 1 5B71CE29
P 3250 3000
F 0 "#PWR026" H 3250 2750 50  0001 C CNN
F 1 "GND" H 3250 2850 50  0000 C CNN
F 2 "" H 3250 3000 50  0001 C CNN
F 3 "" H 3250 3000 50  0001 C CNN
	1    3250 3000
	0    1    1    0   
$EndComp
$Comp
L GND #PWR027
U 1 1 5B71CE5D
P 3250 3300
F 0 "#PWR027" H 3250 3050 50  0001 C CNN
F 1 "GND" H 3250 3150 50  0000 C CNN
F 2 "" H 3250 3300 50  0001 C CNN
F 3 "" H 3250 3300 50  0001 C CNN
	1    3250 3300
	0    1    1    0   
$EndComp
Wire Wire Line
	3250 3000 3300 3000
Wire Wire Line
	3250 3300 3300 3300
Wire Wire Line
	3900 3100 4200 3100
Wire Wire Line
	4900 1600 4900 1950
Text GLabel 4100 1600 0    60   Output ~ 0
PWR_RELAY
Wire Wire Line
	4900 1750 5000 1750
Connection ~ 4900 1750
Text GLabel 4000 2800 2    60   Input ~ 0
PWR_RELAY
Text GLabel 2700 3100 0    60   Input ~ 0
PWR_SW
Text GLabel 2700 2150 2    60   Output ~ 0
PWR_SW
Wire Wire Line
	3100 3100 3300 3100
Wire Wire Line
	2800 3100 2700 3100
$Comp
L +12C #PWR028
U 1 1 5B71EFE0
P 1200 5450
F 0 "#PWR028" H 1200 5300 50  0001 C CNN
F 1 "+12C" H 1200 5600 50  0000 C CNN
F 2 "" H 1200 5450 50  0001 C CNN
F 3 "" H 1200 5450 50  0001 C CNN
	1    1200 5450
	1    0    0    -1  
$EndComp
$Comp
L +12C #PWR029
U 1 1 5B71F010
P 1200 6900
F 0 "#PWR029" H 1200 6750 50  0001 C CNN
F 1 "+12C" H 1200 7050 50  0000 C CNN
F 2 "" H 1200 6900 50  0001 C CNN
F 3 "" H 1200 6900 50  0001 C CNN
	1    1200 6900
	1    0    0    -1  
$EndComp
Wire Wire Line
	1200 6900 1200 6950
Wire Wire Line
	1200 6950 1250 6950
Wire Wire Line
	1200 5450 1200 5500
Wire Wire Line
	1200 5500 1250 5500
NoConn ~ 1250 7150
NoConn ~ 1250 7250
NoConn ~ 1250 7350
NoConn ~ 1250 7450
NoConn ~ 1250 5700
NoConn ~ 1250 5800
NoConn ~ 1250 5900
NoConn ~ 1250 6000
$Comp
L PWR_FLAG #FLG030
U 1 1 5B727E01
P 2600 1150
F 0 "#FLG030" H 2600 1225 50  0001 C CNN
F 1 "PWR_FLAG" H 2600 1300 50  0000 C CNN
F 2 "" H 2600 1150 50  0001 C CNN
F 3 "" H 2600 1150 50  0001 C CNN
	1    2600 1150
	-1   0    0    1   
$EndComp
$Comp
L G5LE-1A K1
U 1 1 5B727F45
P 3250 1500
F 0 "K1" V 3800 1800 50  0000 L CNN
F 1 "G5LE-1A" V 3900 1500 50  0000 L CNN
F 2 "Relays_THT:Relay_SPST_SANYOU_SRD_Series_Form_A" H 3800 1650 50  0001 L CNN
F 3 "" H 4350 1200 50  0001 C CNN
	1    3250 1500
	0    -1   -1   0   
$EndComp
$Comp
L G5LE-1A K2
U 1 1 5B728078
P 4750 1600
F 0 "K2" V 5300 1900 50  0000 L CNN
F 1 "G5LE-1A" V 5400 1600 50  0000 L CNN
F 2 "Relays_THT:Relay_SPST_SANYOU_SRD_Series_Form_A" H 5300 1750 50  0001 L CNN
F 3 "" H 5850 1300 50  0001 C CNN
	1    4750 1600
	0    -1   -1   0   
$EndComp
$Comp
L +12C #PWR031
U 1 1 5B732948
P 8200 1750
F 0 "#PWR031" H 8200 1600 50  0001 C CNN
F 1 "+12C" H 8200 1900 50  0000 C CNN
F 2 "" H 8200 1750 50  0001 C CNN
F 3 "" H 8200 1750 50  0001 C CNN
	1    8200 1750
	-1   0    0    1   
$EndComp
Wire Wire Line
	2600 1150 2600 1100
Connection ~ 2600 1100
Wire Wire Line
	3350 1100 3400 1100
Wire Wire Line
	3400 2350 2550 2350
Wire Wire Line
	2550 2350 2550 2150
Connection ~ 2550 2150
Connection ~ 3400 1850
Wire Wire Line
	3900 2800 4000 2800
$EndSCHEMATC
