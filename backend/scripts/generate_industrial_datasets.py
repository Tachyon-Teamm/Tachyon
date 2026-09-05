#!/usr/bin/env python3
"""
Industrial Synthetic Dataset Generator for Problem Statement 26099
AI-Driven Standardization and Harmonization of Material Codes Across CPSEs
Host Organization: Chennai Petroleum Corporation Limited (CPCL) / MoPNG
"""

import os
import csv
import zipfile

def generate_datasets(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # ---------------------------------------------------------
    # 1. CPCL Dataset (Refinery Standard Format)
    # Header: MATERIAL_NO, ITEM_SPEC, UNIT_OF_MEASURE, LAST_PO_PRICE, QUANTITY, VENDOR_NAME, HSN_CODE
    # ---------------------------------------------------------
    cpcl_rows = [
        # --- Group 1: Valves (Identical & Invariant Vetoes) ---
        ["CPCL-VLV-401416", "VLV GATE 6IN 300# CS FLG ASME B16.34 WCB", "Nos", 14500.0, 250.0, "L&T Valves Limited", "84818030"],
        ["CPCL-VLV-401417", "VALVE 2\" 150# CS FLANGED GATE WCB", "EA", 4200.0, 400.0, "L&T Valves Limited", "84818030"],
        ["CPCL-VLV-401419", "BALL VALVE 3\" 150# FLANGED CF8M SS316", "Nos", 9800.0, 150.0, "Microfinish Valves", "84818030"],
        ["CPCL-VLV-401420", "VALVE CHECK 4IN 300# DUAL PLATE CS A216 WCB", "EA", 8200.0, 180.0, "Advance Valves India", "84813000"],
        ["CPCL-VLV-401421", "GLOBE VALVE 2\" 600# FORGED A105 SW", "Nos", 6500.0, 120.0, "Audco India Ltd", "84818030"],
        ["CPCL-VLV-401422", "BUTTERFLY VALVE 8IN 150# WAFER TYPE CI BODY EPDM LINED", "EA", 7200.0, 90.0, "Dembla Valves Ltd", "84818030"],
        ["CPCL-VLV-401423", "PLUG VALVE 3\" 300# SLEEVED PTFE CS WCB FLANGED", "Nos", 11500.0, 75.0, "Xomox India Pvt Ltd", "84818030"],
        ["CPCL-VLV-401424", "SAFETY RELIEF VALVE 2IN X 3IN 150# X 300# CS SET 10 BAR", "SET", 48000.0, 25.0, "Tyco Sanmar Ltd", "84814000"],
        ["CPCL-VLV-401425", "NEEDLE VALVE 1/2\" NPT 6000 PSI SS316 FOR INSTRUMENTATION", "EA", 1650.0, 350.0, "Swagelok India", "84818030"],
        ["CPCL-VLV-401426", "CONTROL VALVE 4\" 300# GLOBE LINEAR WCB WITH PNEUMATIC ACTUATOR", "SET", 185000.0, 15.0, "Fisher Emerson India", "84818030"],

        # --- Group 2: Pipes, Tubes & Fittings ---
        ["CPCL-PIP-401715", "PIPE CS SMLS 4\" SCH 40 ASTM A106 GR.B", "MTR", 2450.0, 1200.0, "Jindal Saw Ltd", "73041910"],
        ["CPCL-PIP-401716", "PIPE CS SMLS 6\" SCH 40 ASTM A106", "MTR", 3850.0, 600.0, "Maharashtra Seamless", "73041910"],
        ["CPCL-PIP-401717", "PIPE CS SMLS 2\" SCH 80 ASTM A106 GR.B HIGH PRESSURE", "MTR", 1750.0, 900.0, "ISMT Limited", "73041910"],
        ["CPCL-PIP-401718", "PIPE SS316 SMLS 2\" SCH 40S ASTM A312 TP316L", "MTR", 4600.0, 350.0, "Ratnamani Metals", "73044100"],
        ["CPCL-PIP-401719", "PIPE ALLOY STEEL 4\" SCH 80 ASTM A335 GR.P11", "MTR", 5900.0, 250.0, "Jindal Saw Ltd", "73045910"],
        ["CPCL-FLG-401715", "FLANGE 6\" 300# WNRF ANSI B16.5 CS ASTM A105", "Nos", 3200.0, 300.0, "EIL Approved Vendor", "73072100"],
        ["CPCL-FLG-401716", "FLANGE 4\" 150# SORF ANSI B16.5 CS A105", "Nos", 1450.0, 450.0, "Texas Flange India", "73072100"],
        ["CPCL-FLG-401717", "BLIND FLANGE 6\" 300# RF CS ASTM A105", "Nos", 2800.0, 150.0, "EIL Approved Vendor", "73072100"],
        ["CPCL-FIT-401718", "ELBOW 90 DEG 4\" SCH 40 B/W ASTM A234 WPB", "EA", 950.0, 320.0, "Tube Products India", "73079310"],
        ["CPCL-FIT-401719", "EQUAL TEE 6\" SCH 40 BUTTWELD CS ASTM A234 WPB", "EA", 1850.0, 180.0, "Tube Products India", "73079310"],

        # --- Group 3: Gaskets & Fasteners ---
        ["CPCL-GSK-312015", "GASKET SPIRAL WOUND 4\" 300# CS/SS316 GRAPHITE", "Nos", 480.0, 800.0, "Champion Seals Ltd", "84841000"],
        ["CPCL-GSK-312016", "GASKET SPIRAL WOUND 6\" 300# SS316/GRAPHITE FILLER", "EA", 620.0, 600.0, "Champion Seals Ltd", "84841000"],
        ["CPCL-GSK-312017", "GASKET RING JOINT R-24 OCTAGONAL SOFT IRON RTJ", "Nos", 1150.0, 200.0, "Spiratec Gaskets", "84841000"],
        ["CPCL-GSK-312018", "CAF GASKET COMPRESSED ASBESTOS FREE 3MM THK 4\" 150#", "EA", 180.0, 500.0, "Hindustan Composites", "84841000"],
        ["CPCL-FST-311616", "STUD BOLT ASTM A193 B7 WITH 2 NUTS A194 2H M20 X 120", "SET", 185.0, 2500.0, "Unbrako Fasteners", "73181500"],
        ["CPCL-FST-311617", "STUD BOLT ASTM A193 B7 WITH 2 NUTS A194 2H M24 X 160", "SET", 295.0, 1800.0, "Unbrako Fasteners", "73181500"],
        ["CPCL-FST-311618", "HEX BOLT ASTM A307 GR.B M16 X 65 WITH NUT", "SET", 45.0, 4000.0, "Sundram Fasteners", "73181500"],
        ["CPCL-FST-311619", "SS316 STUD BOLT A193 B8M WITH 2 NUTS A194 8M M20 X 120", "SET", 420.0, 800.0, "Apcotex Fasteners", "73181500"],

        # --- Group 4: Bearings (Identical & Clearance Vetoes) ---
        ["CPCL-BRG-311715", "BRG 6205-2RS1 SKF DEEP GROOVE BALL", "EA", 920.0, 500.0, "SKF India Ltd", "84821010"],
        ["CPCL-BRG-311716", "BEARING 6308-2RS SKF DEEP GROOVE BALL BEARING", "Nos", 1850.0, 300.0, "SKF India Ltd", "84821010"],
        ["CPCL-BRG-311717", "SPHERICAL ROLLER BEARING 22218 EK/C3 FAG", "EA", 8400.0, 120.0, "Schaeffler India", "84823000"],
        ["CPCL-BRG-311718", "TAPER ROLLER BEARING 32214 TIMKEN", "Nos", 4200.0, 150.0, "Timken India Ltd", "84822000"],
        ["CPCL-BRG-311719", "CYLINDRICAL ROLLER BEARING NU 312 ECP SKF", "EA", 5100.0, 100.0, "SKF India Ltd", "84825000"],

        # --- Group 5: Lubricants & Greases (Packaged & Bulk) ---
        ["CPCL-LUB-151215", "GREASE MOBILITH SHC 100 - 18KG BUCKET", "BKT", 12600.0, 80.0, "ExxonMobil Lubricants", "27101980"],
        ["CPCL-OIL-151216", "SHELL OMALA S2 G 220 INDUSTRIAL GEAR OIL 209L", "DRM", 46000.0, 45.0, "Shell India Markets", "27101980"],
        ["CPCL-OIL-151217", "TURBINE OIL ISO VG 46 SERVO PRIME 46 210L", "DRM", 38500.0, 60.0, "Indian Oil Corp Ltd", "27101980"],
        ["CPCL-OIL-151218", "HYDRAULIC OIL ISO VG 68 ENKLO 68 210L DRUM", "DRM", 34000.0, 80.0, "Hindustan Petroleum", "27101980"],
        ["CPCL-LUB-151219", "HIGH TEMP SYNTHETIC GREASE MOBILGREASE 28 (18KG)", "BKT", 16800.0, 30.0, "ExxonMobil Lubricants", "27101980"],

        # --- Group 6: Pumps, Mechanical Seals & Spares ---
        ["CPCL-PMP-401515", "CENTRIFUGAL WATER PUMP 50M3/HR HEAD 60M (COMPLETE)", "EA", 280000.0, 12.0, "Kirloskar Brothers", "84137010"],
        ["CPCL-MCH-401418", "MECH SEAL CARTRIDGE PUMP P-101A (SET)", "SET", 45000.0, 30.0, "Flowserve India", "84841000"],
        ["CPCL-PMP-401516", "ROTARY POSITIVE DISPLACEMENT GEAR PUMP 10M3/HR", "EA", 95000.0, 8.0, "Tushaco Pumps Ltd", "84136010"],
        ["CPCL-MCH-401422", "COUPLING FLEXIBLE LOVEJOY SIZE L-100 WITH SPIDER", "SET", 2800.0, 80.0, "Lovejoy India", "84836090"],

        # --- Group 7: Electrical Equipment ---
        ["CPCL-ELE-850410", "HT XLPE POWER CABLE 3C X 240 SQMM 11KV AL", "MTR", 1450.0, 1500.0, "Polycab India", "85446090"],
        ["CPCL-ELE-850411", "LT POWER CABLE 4C X 50 SQMM XLPE ARMORED AL 1.1KV", "MTR", 380.0, 2500.0, "Havells India", "85444990"],
        ["CPCL-ELE-850412", "INSTRUMENTATION CABLE 12 PAIR 1.5 SQMM OVERALL SHIELDED", "MTR", 290.0, 3000.0, "KEI Industries Ltd", "85444290"],
        ["CPCL-ELE-850413", "3-PHASE INDUCTION MOTOR 45KW 4-POLE 415V FOOT MOUNTED IE3", "EA", 125000.0, 10.0, "Bharat Bijlee Ltd", "85015290"],
        ["CPCL-ELE-850414", "FLAMEPROOF EX-D PUSH BUTTON STATION START-STOP 2NO+2NC", "Nos", 3400.0, 60.0, "Baliga Lighting Eqpt", "85365090"],

        # --- Group 8: Instrumentation & Automation ---
        ["CPCL-INS-902610", "PRESSURE TRANSMITTER 0-10 BAR 4-20MA HART SMART", "EA", 34000.0, 50.0, "Yokogawa India", "90262000"],
        ["CPCL-INS-902611", "TEMPERATURE TRANSMITTER HEAD MOUNTED RTD PT100 4-20MA", "EA", 14500.0, 80.0, "Rosemount Emerson", "90251990"],
        ["CPCL-INS-902612", "MAGNETIC LEVEL GAUGE SS316 C-TO-C 1200MM 300# FLANGED", "SET", 42000.0, 20.0, "Chemtrols Industries", "90261020"],
        ["CPCL-INS-902613", "VORTEX FLOW TRANSMITTER 3IN 300# WAFER TYPE HART", "EA", 78000.0, 15.0, "Yokogawa India", "90261010"],
        ["CPCL-INS-902614", "PRESSURE GAUGE 0-16 KG/CM2 4\" DIAL 1/2\" NPT BOTTOM ENTRY", "EA", 1850.0, 200.0, "Baumer India", "90262000"]
    ]

    # ---------------------------------------------------------
    # 2. IOCL Dataset (SAP S/4HANA Enterprise Format)
    # Header: SAP_MATNR, MATERIAL_DESC, BASE_UOM, NETPR, PO_QTY, VENDOR_NAME, COMMODITY_CODE
    # ---------------------------------------------------------
    iocl_rows = [
        # --- Group 1: Valves (Identical & Invariant Vetoes) ---
        ["IOCL-774102", "VALVE, GATE, 150MM, CLASS 300, WCB, RF", "EA", 11200.0, 600.0, "Larsen & Toubro Ltd - Valve Div", "84818030"],
        ["IOCL-889999", "VALVE 2\" 300# CS FLG GATE WCB", "EA", 6800.0, 300.0, "L&T Valves", "84818030"],
        ["IOCL-889111", "BALL VALVE 3 INCH 150# FULL BORE SS316", "EA", 9400.0, 220.0, "L&T Valves", "84818030"],
        ["IOCL-774103", "DUAL PLATE CHECK VALVE 4\" 300# FLANGED CS WCB", "Numbers", 7600.0, 250.0, "Advance Valves", "84813000"],
        ["IOCL-774104", "FORGED GLOBE VALVE 2\" 600# A105 SOCKET WELD OS&Y", "EA", 6100.0, 180.0, "Audco India", "84818030"],
        ["IOCL-774105", "BUTTERFLY VALVE 8\" 150# WAFER TYPE CI/EPDM LINED", "EA", 6850.0, 140.0, "Dembla Valves", "84818030"],
        ["IOCL-774106", "3 INCH PLUG VALVE SLEEVED PTFE CS 300#", "Numbers", 10800.0, 95.0, "Xomox India", "84818030"],
        ["IOCL-774107", "PRESSURE SAFETY VALVE 2\"X3\" 150X300# CS SET PRESSURE 10 BAR", "EA", 46500.0, 40.0, "Tyco Sanmar", "84814000"],
        ["IOCL-774108", "NEEDLE VALVE 1/2\" NPTF 6000# SS316 INTEGRAL BONNET", "Numbers", 1520.0, 500.0, "Parker Hannifin India", "84818030"],
        ["IOCL-774109", "PNEUMATIC CONTROL VALVE 4\" 300# GLOBE DIAPHRAGM ACTUATED", "SET", 178000.0, 20.0, "Emerson Process India", "84818030"],

        # --- Group 2: Pipes, Tubes & Fittings ---
        ["IOCL-889555", "PIPE CS 4\" SCH 40 A106 GR B SEAMLESS", "M", 2280.0, 2000.0, "Maharashtra Seamless Ltd", "73041910"],
        ["IOCL-889716", "PIPE CS SMLS 6\" SCH 80 ASTM A106", "MTR", 5100.0, 450.0, "Jindal Saw", "73041910"],
        ["IOCL-774201", "PIPE CS SEAMLESS 2\" SCH 80 ASTM A106 GRADE B", "MTR", 1680.0, 1500.0, "ISMT Limited", "73041910"],
        ["IOCL-774202", "STAINLESS STEEL PIPE 2\" SCH 40S ASTM A312 TP316L SMLS", "M", 4350.0, 600.0, "Ratnamani Metals & Tubes", "73044100"],
        ["IOCL-774203", "ALLOY STEEL PIPE 4\" SCH 80 ASTM A335 GRADE P11 SEAMLESS", "MTR", 5650.0, 400.0, "Jindal Saw", "73045910"],
        ["IOCL-889444", "FLANGE 6\" 300# WNRF ASME B16.5 A105", "EA", 2950.0, 550.0, "Engineers India Ltd Approved", "73072100"],
        ["IOCL-774205", "SLIP ON FLANGE 4\" 150# ANSI B16.5 A105 FORGED CS", "EA", 1380.0, 650.0, "Texas Flange", "73072100"],
        ["IOCL-774206", "BLIND FLANGE 6 INCH 300 LBS RF CS A105", "EA", 2650.0, 220.0, "EIL Approved", "73072100"],
        ["IOCL-774207", "4 INCH BUTTWELD ELBOW 90 DEG SCH 40 ASTM A234 WPB", "Numbers", 880.0, 500.0, "Tube Products", "73079310"],
        ["IOCL-774208", "EQUAL TEE 6\" SCH40 WPB BUTTWELD ASME B16.9", "EA", 1740.0, 280.0, "Tube Products", "73079310"],

        # --- Group 3: Gaskets & Fasteners ---
        ["IOCL-889333", "4\" SPIRAL GASKET JAALI WALA 300# SS316/GRAPHITE", "EA", 420.0, 1500.0, "Champion Seals", "84841000"],
        ["IOCL-774301", "GASKET SPIRAL WOUND 6\" 300# SS316 INNER RING GRAPHITE", "Numbers", 580.0, 950.0, "Champion Seals Ltd", "84841000"],
        ["IOCL-774302", "RING JOINT GASKET R-24 SOFT IRON FOR 300# FLANGES", "EA", 1080.0, 320.0, "Spiratec Gaskets", "84841000"],
        ["IOCL-774303", "NON ASBESTOS FIBER GASKET 4\" 150# 3MM THICK", "EA", 165.0, 800.0, "Hindustan Composites", "84841000"],
        ["IOCL-889888", "STUD BOLT B7 WITH 2H HEX NUTS M20 X 120MM", "Numbers", 165.0, 4000.0, "Sundram Fasteners", "73181500"],
        ["IOCL-774305", "ALLOY STEEL STUD BOLT M24 X 160MM A193 B7 W/ 2 NUTS 2H", "SET", 270.0, 2800.0, "Unbrako Fasteners", "73181500"],
        ["IOCL-774306", "CS HEX BOLT M16 X 65 ASTM A307 WITH HEX NUT", "SET", 40.0, 6000.0, "Sundram Fasteners", "73181500"],
        ["IOCL-774307", "STAINLESS STEEL STUD BOLT M20 X 120 A193 B8M WITH 2H NUTS", "SET", 390.0, 1200.0, "Apcotex", "73181500"],

        # --- Group 4: Bearings (Identical & Clearance Vetoes) ---
        ["IOCL-889501", "BEARING NO 6205 2RS1 / C3 SKF", "Nos", 980.0, 850.0, "SKF Bearings", "84821010"],
        ["IOCL-774401", "DEEP GROOVE BALL BEARING 6308-2RS SKF", "EA", 1750.0, 500.0, "SKF India", "84821010"],
        ["IOCL-774402", "SPHERICAL ROLLER BEARING 22218 EK C3 FAG GERMANY", "Numbers", 8100.0, 220.0, "Schaeffler India", "84823000"],
        ["IOCL-774403", "TIMKEN TAPER ROLLER BEARING 32214", "EA", 3950.0, 260.0, "Timken India", "84822000"],
        ["IOCL-774404", "CYLINDRICAL ROLLER BEARING NU 312 ECP SKF", "Nos", 4850.0, 160.0, "SKF India", "84825000"],

        # --- Group 5: Lubricants & Greases (Substitutes & UOMs) ---
        ["IOCL-889612", "GREASE MOBILITH SHC 100 SYNTHETIC", "KG", 750.0, 1500.0, "Mobil Oil India", "27101980"],
        ["IOCL-889700", "SERVOMESH SP 220 INDUSTRIAL GEAR OIL 210L", "DRM", 41500.0, 90.0, "Indian Oil Corp - R&D Lubricants", "27101980"],
        ["IOCL-774501", "SERVO PRIME 46 INDUSTRIAL TURBINE OIL 210L BARREL", "DRM", 37000.0, 110.0, "Indian Oil Corp Ltd", "27101980"],
        ["IOCL-774502", "SERVO SYSTEM 68 HYDRAULIC OIL 210L DRUM", "DRM", 33200.0, 140.0, "Indian Oil Corp Ltd", "27101980"],
        ["IOCL-774503", "SERVOGEM SUPER HT SYNTHETIC GREASE 182KG BARREL", "DRM", 102000.0, 25.0, "Indian Oil Corp Ltd", "27101980"],

        # --- Group 6: Pumps, Mechanical Seals & Spares ---
        ["IOCL-889515", "PUMP IMPELLER FOR WATER PUMP 50M3/HR (SPARE)", "EA", 32000.0, 25.0, "Kirloskar Brothers", "84139120"],
        ["IOCL-889777", "ROTARY SEAL RING FOR PUMP P-101A (SPARE PART)", "EA", 8500.0, 40.0, "Flowserve", "84841000"],
        ["IOCL-774601", "POSITIVE DISPLACEMENT GEAR PUMP 10 M3/HR FUEL OIL", "EA", 91000.0, 15.0, "Tushaco Pumps", "84136010"],
        ["IOCL-774602", "LOVEJOY JAW COUPLING L-100 COMPLETE SET", "SET", 2650.0, 140.0, "Lovejoy India", "84836090"],

        # --- Group 7: Electrical Equipment ---
        ["IOCL-889410", "11KV HT CABLE 3 CORE 240 SQMM XLPE AL COND", "MTR", 1380.0, 3000.0, "Havells India", "85446090"],
        ["IOCL-774701", "LT POWER CABLE 4 CORE 50 SQMM XLPE ARMOURED ALUMINIUM", "MTR", 365.0, 4000.0, "Polycab India", "85444990"],
        ["IOCL-774702", "SHIELDED INSTRUMENTATION CABLE 12P X 1.5 SQMM CU", "M", 275.0, 4500.0, "KEI Industries", "85444290"],
        ["IOCL-774703", "45 KW 4-POLE 415V 50HZ INDUCTION MOTOR B3 IE3 EFFICIENCY", "EA", 119000.0, 18.0, "Bharat Bijlee", "85015290"],
        ["IOCL-774704", "EXPLOSION PROOF PUSH BUTTON STATION START STOP FLAMEPROOF", "EA", 3250.0, 90.0, "Baliga Lighting", "85365090"],

        # --- Group 8: Instrumentation & Automation ---
        ["IOCL-889610", "PRESSURE TRANSMITTER 0-10 KG/CM2 4-20 MA D/P", "EA", 31500.0, 80.0, "Emerson Process Management", "90262000"],
        ["IOCL-774801", "HEAD MOUNTED TEMPERATURE TRANSMITTER RTD PT100 4-20MA HART", "Numbers", 13900.0, 120.0, "Emerson Rosemount", "90251990"],
        ["IOCL-774802", "MAGNETIC LEVEL INDICATOR MLG 1200MM C-C SS316 300# RF", "SET", 39800.0, 35.0, "Chemtrols", "90261020"],
        ["IOCL-774803", "3\" 300# VORTEX FLOWMETER WAFER TYPE HART PROTOCOL", "EA", 74500.0, 22.0, "Yokogawa", "90261010"],
        ["IOCL-774804", "PRESSURE GAUGE 0-16 BAR 100MM DIAL 1/2\" NPTM BOTTOM", "Numbers", 1720.0, 300.0, "Baumer India", "90262000"]
    ]

    # ---------------------------------------------------------
    # 3. BPCL Dataset (Refining & Marketing Format)
    # Header: ITEM_CODE, SHORT_TEXT, UOM, UNIT_PRICE, ANNUAL_DEMAND, SUPPLIER_NAME, HSN
    # ---------------------------------------------------------
    bpcl_rows = [
        # --- Group 1: Valves (Identical & Invariant Vetoes) ---
        ["BPCL-889012", "6 INCH GATE VALVE FLANGED 300# WCB OS&Y", "Numbers", 12800.0, 400.0, "Microfinish Valves Pvt Ltd", "84818030"],
        ["BPCL-445999", "GATE VALVE 2 INCH 150# FLANGED CS", "EA", 4050.0, 350.0, "Microfinish", "84818030"],
        ["BPCL-445112", "3\" BALL VALVE 150# FLG STAINLESS STEEL 316", "Numbers", 9600.0, 180.0, "Microfinish Valves", "84818030"],
        ["BPCL-663101", "CHECK VALVE 4\" 300# DUAL PLATE WCB FLANGED", "EA", 7900.0, 200.0, "Advance Valves", "84813000"],
        ["BPCL-663102", "2 INCH FORGED GLOBE VALVE 600# A105 SW", "Nos", 6250.0, 150.0, "Audco India", "84818030"],
        ["BPCL-663103", "WAFER BUTTERFLY VALVE 8\" 150# CI BODY EPDM SEAT", "Numbers", 6950.0, 110.0, "Dembla Valves", "84818030"],
        ["BPCL-663104", "PLUG VALVE 3\" CLASS 300 PTFE SLEEVED WCB FLANGED", "Nos", 11100.0, 80.0, "Xomox India", "84818030"],
        ["BPCL-663105", "SAFETY VALVE 2\" X 3\" 150# X 300# SET AT 10 BAR", "SET", 47200.0, 30.0, "Tyco Sanmar", "84814000"],
        ["BPCL-663106", "INSTRUMENT NEEDLE VALVE 1/2\" NPT 6000 PSI SS316", "EA", 1580.0, 400.0, "Swagelok India", "84818030"],
        ["BPCL-663107", "4\" 300# GLOBE CONTROL VALVE WITH PNEUMATIC DIAPHRAGM ACTUATOR", "SET", 181000.0, 16.0, "Fisher Emerson", "84818030"],

        # --- Group 2: Pipes, Tubes & Fittings ---
        ["BPCL-445888", "4 INCH SEAMLESS PIPE SCH40 A106", "MTR", 2380.0, 1500.0, "Jindal Saw", "73041910"],
        ["BPCL-663201", "PIPE CS SMLS 6\" SCH 40 ASTM A106 GRADE B", "MTR", 3720.0, 750.0, "Maharashtra Seamless", "73041910"],
        ["BPCL-663202", "PIPE SEAMLESS 2\" SCH 80 CS ASTM A106", "MTR", 1710.0, 1100.0, "ISMT Limited", "73041910"],
        ["BPCL-663203", "PIPE SS316L SMLS 2\" SCH 40S A312", "MTR", 4480.0, 450.0, "Ratnamani Metals", "73044100"],
        ["BPCL-663204", "ALLOY STEEL PIPE 4\" SCH 80 ASTM A335 P11", "MTR", 5780.0, 300.0, "Jindal Saw", "73045910"],
        ["BPCL-445444", "WNRF FLANGE 6 INCH 300 LBS ASTM A105", "Numbers", 3050.0, 350.0, "Texas Flange India", "73072100"],
        ["BPCL-663205", "SORF FLANGE 4\" 150# CS ASTM A105", "Numbers", 1410.0, 500.0, "Texas Flange", "73072100"],
        ["BPCL-663206", "BLIND FLANGE 6\" 300# ANSI B16.5 A105", "Nos", 2720.0, 180.0, "EIL Approved", "73072100"],
        ["BPCL-663207", "ELBOW 90 DEG 4\" SCH 40 CS BUTTWELD A234 WPB", "EA", 910.0, 400.0, "Tube Products", "73079310"],
        ["BPCL-663208", "EQUAL TEE 6\" SCH 40 BUTTWELD WPB ASTM A234", "EA", 1790.0, 220.0, "Tube Products", "73079310"],

        # --- Group 3: Gaskets & Fasteners ---
        ["BPCL-445333", "GASKET SPIRAL 4 INCH 300# GRAPHITE/SS316", "EA", 450.0, 1000.0, "Champion Seals", "84841000"],
        ["BPCL-663301", "GASKET SPIRAL WOUND 6\" 300# CS/SS316 GRAPHITE", "EA", 595.0, 750.0, "Champion Seals", "84841000"],
        ["BPCL-663302", "OCTAGONAL RING GASKET R-24 SOFT IRON 300#", "Numbers", 1120.0, 250.0, "Spiratec Gaskets", "84841000"],
        ["BPCL-663303", "COMPRESSED NON-ASBESTOS FIBER GASKET 4\" 150#", "EA", 172.0, 650.0, "Hindustan Composites", "84841000"],
        ["BPCL-445889", "HIGH TENSILE STUD BOLT B7/2H M20X120", "Nos", 172.0, 3000.0, "Apcotex Fasteners", "73181500"],
        ["BPCL-663305", "STUD BOLT ASTM A193 B7 WITH 2 NUTS 2H M24 X 160", "SET", 282.0, 2200.0, "Unbrako Fasteners", "73181500"],
        ["BPCL-663306", "HEX BOLT WITH NUT M16 X 65 ASTM A307 GR.B", "SET", 42.0, 4500.0, "Sundram Fasteners", "73181500"],
        ["BPCL-663307", "SS316 STUD BOLT A193 B8M WITH 2 NUTS M20 X 120", "SET", 405.0, 950.0, "Apcotex", "73181500"],

        # --- Group 4: Bearings (Identical & Clearance Vetoes) ---
        ["BPCL-445501", "DEEP GROOVE BALL BEARING 6205-2RS1", "Numbers", 890.0, 600.0, "SKF India", "84821010"],
        ["BPCL-663401", "6308-2RS SKF DEEP GROOVE BALL BEARING", "Numbers", 1790.0, 380.0, "SKF India", "84821010"],
        ["BPCL-663402", "SPHERICAL ROLLER BEARING 22218 EK/C3 FAG", "EA", 8250.0, 160.0, "Schaeffler India", "84823000"],
        ["BPCL-663403", "TIMKEN TAPER ROLLER BEARING 32214", "Nos", 4050.0, 200.0, "Timken India", "84822000"],
        ["BPCL-663404", "CYLINDRICAL ROLLER BEARING NU 312 ECP SKF", "EA", 4950.0, 130.0, "SKF India", "84825000"],

        # --- Group 5: Lubricants & Greases (Substitutes & UOMs) ---
        ["BPCL-445612", "MOBILITH SHC 100 - 180KG DRUM", "DRM", 117000.0, 20.0, "ExxonMobil India", "27101980"],
        ["BPCL-445700", "MAK AMOCAM 220 INDUSTRIAL GEAR OIL 210L", "DRM", 42200.0, 60.0, "Bharat Petroleum - MAK Lubes", "27101980"],
        ["BPCL-663501", "MAK TURBINE OIL 46 - 210L DRUM", "DRM", 37800.0, 80.0, "Bharat Petroleum - MAK Lubes", "27101980"],
        ["BPCL-663502", "MAK HYDROL 68 HYDRAULIC OIL 210L BARREL", "DRM", 33600.0, 100.0, "Bharat Petroleum - MAK Lubes", "27101980"],
        ["BPCL-663503", "SHELL GADUS S5 V100 2 ADVANCED SYNTHETIC GREASE 18KG", "BKT", 14200.0, 35.0, "Shell India", "27101980"],

        # --- Group 6: Pumps, Mechanical Seals & Spares ---
        ["BPCL-663601", "CENTRIFUGAL BARE SHAFT PUMP 50M3/HR HEAD 60M", "EA", 215000.0, 8.0, "Kirloskar Brothers", "84137010"],
        ["BPCL-663602", "CARTRIDGE MECHANICAL SEAL FOR PUMP P-101A", "SET", 43500.0, 35.0, "Flowserve India", "84841000"],
        ["BPCL-663603", "ROTARY GEAR PUMP 10M3/HR HEAVY OIL SERVICE", "EA", 93000.0, 10.0, "Tushaco Pumps", "84136010"],
        ["BPCL-663604", "LOVEJOY JAW FLEXIBLE COUPLING L-100 COMPLETE", "SET", 2720.0, 100.0, "Lovejoy India", "84836090"],

        # --- Group 7: Electrical Equipment ---
        ["BPCL-445410", "CABLE HT 11KV XLPE 3CX240 SQMM ALUMINIUM", "MTR", 1410.0, 2000.0, "Polycab India", "85446090"],
        ["BPCL-663701", "LT ARMOURED POWER CABLE 4C X 50 SQMM XLPE AL", "MTR", 372.0, 3000.0, "Havells India", "85444990"],
        ["BPCL-663702", "OVERALL SHIELDED INSTRUMENTATION CABLE 12P 1.5 SQMM CU", "MTR", 282.0, 3500.0, "KEI Industries", "85444290"],
        ["BPCL-663703", "INDUCTION MOTOR 45KW 4-POLE 415V FOOT MOUNTED EFF2/IE3", "EA", 122000.0, 12.0, "Bharat Bijlee", "85015290"],
        ["BPCL-663704", "FLAMEPROOF LOCAL CONTROL PUSH BUTTON STATION START-STOP", "Numbers", 3320.0, 75.0, "Baliga Lighting", "85365090"],

        # --- Group 8: Instrumentation & Automation ---
        ["BPCL-445610", "SMART DIFFERENTIAL PRESSURE TRANSMITTER 4-20MA", "EA", 32800.0, 60.0, "ABB India Ltd", "90262000"],
        ["BPCL-663801", "TEMPERATURE TRANSMITTER WITH RTD SENSOR PT100 4-20MA", "EA", 14100.0, 90.0, "Rosemount Emerson", "90251990"],
        ["BPCL-663802", "MAGNETIC LEVEL GAUGE SS316 1200MM FLANGED 300#", "SET", 41200.0, 25.0, "Chemtrols Industries", "90261020"],
        ["BPCL-663803", "VORTEX FLOWMETER 3IN 300# WAFER TYPE WITH HART", "EA", 76000.0, 18.0, "Yokogawa", "90261010"],
        ["BPCL-663804", "PRESSURE GAUGE 0-16 BAR 4\" DIAL 1/2\" NPT BOTTOM CONNECTION", "EA", 1780.0, 240.0, "Baumer India", "90262000"]
    ]

    # ---------------------------------------------------------
    # 4. Multi-Sector CPSEs (ONGC, NTPC, SAIL, BHEL, COALINDIA)
    # ---------------------------------------------------------
    ongc_rows = [
        ["ITEM_ID", "DESCRIPTION", "UOM", "PO_RATE", "QUANTITY", "SUPPLIER", "HSN_CODE"],
        ["ONGC-DRL-001", "DRILL COLLAR 6-1/2 INCH OD 4-1/2 INCH IF CONNECTION API SPEC 7-1", "EA", 480000.0, 15.0, "National Oilwell Varco", "84314300"],
        ["ONGC-VLV-002", "GATE VALVE 6\" 300# CS WCB FLANGED DRILLING MANIFOLD", "Nos", 15200.0, 120.0, "L&T Valves Limited", "84818030"],
        ["ONGC-PIP-003", "PIPE CASING 9-5/8 INCH 47 LB/FT L-80 PREMIUM THREAD API 5CT", "MTR", 12500.0, 800.0, "Jindal Saw Ltd", "73042990"],
        ["ONGC-PIP-004", "PIPE CS SMLS 4\" SCH 40 ASTM A106 GR.B OFFSHORE SERVICE", "MTR", 2550.0, 1000.0, "Maharashtra Seamless", "73041910"],
        ["ONGC-BRG-005", "DEEP GROOVE BALL BEARING 6205-2RS1 SKF", "EA", 950.0, 300.0, "SKF India Ltd", "84821010"],
        ["ONGC-LUB-006", "DRILL RIG GREASE MOBILITH SHC 100 SYNTHETIC (18KG)", "BKT", 13200.0, 40.0, "ExxonMobil Lubricants", "27101980"],
        ["ONGC-FST-007", "STUD BOLT ASTM A193 B7 WITH 2 NUTS 2H M20 X 120MM OFFSHORE", "SET", 195.0, 1500.0, "Unbrako Fasteners", "73181500"],
        ["ONGC-ELE-008", "SUBMERSIBLE ESP POWER CABLE 5KV 3C #4 AWG EPDM OILWELL", "MTR", 3200.0, 2000.0, "Schlumberger Offshore", "85446090"],
        ["ONGC-INS-009", "SMART PRESSURE TRANSMITTER 0-10 BAR 4-20MA HART EEX-D", "EA", 36500.0, 45.0, "Yokogawa India", "90262000"],
        ["ONGC-FLG-010", "WNRF FLANGE 6\" 300# ANSI B16.5 A105 FORGED CS", "Nos", 3350.0, 150.0, "Texas Flange India", "73072100"]
    ]

    ntpc_rows = [
        ["MAT_CODE", "ITEM_SPECIFICATION", "UNIT", "UNIT_PRICE", "ANNUAL_DEMAND", "VENDOR", "COMMODITY_CODE"],
        ["NTPC-BLR-101", "BOILER TUBE 63.5 MM OD X 5.6 MM THK SA213 T91 SUPERHEATER", "MTR", 8200.0, 600.0, "Jindal Saw Ltd", "73045910"],
        ["NTPC-VLV-102", "HIGH PRESSURE FORGED GLOBE VALVE 2\" 600# A105 SW BOILER SERVICE", "EA", 6600.0, 80.0, "Audco India Ltd", "84818030"],
        ["NTPC-PIP-103", "PIPE CS SMLS 4\" SCH 40 ASTM A106 GR.B ASH SLURRY LINE", "MTR", 2420.0, 1500.0, "Maharashtra Seamless", "73041910"],
        ["NTPC-BRG-104", "SPHERICAL ROLLER BEARING 22218 EK/C3 FAG COAL PULVERIZER", "EA", 8600.0, 90.0, "Schaeffler India", "84823000"],
        ["NTPC-BRG-105", "BALL BEARING 6205-2RS1 SKF AUXILIARY MOTOR DRIVE", "Nos", 910.0, 400.0, "SKF India Ltd", "84821010"],
        ["NTPC-OIL-106", "SERVO PRIME 46 STEAM TURBINE OIL 210L DRUM", "DRM", 38200.0, 75.0, "Indian Oil Corp Ltd", "27101980"],
        ["NTPC-FST-107", "STUD BOLT B7/2H M20 X 120MM FLANGE MOUNTING STEAM LINE", "SET", 182.0, 2000.0, "Sundram Fasteners", "73181500"],
        ["NTPC-ELE-108", "HT POWER CABLE 11KV 3C X 240 SQMM XLPE ALUMINIUM CONDUCTOR", "MTR", 1420.0, 2500.0, "Havells India", "85446090"],
        ["NTPC-ELE-109", "3-PHASE SQUIRREL CAGE INDUCTION MOTOR 45KW 4-POLE 415V IE3", "EA", 124000.0, 14.0, "Bharat Bijlee Ltd", "85015290"],
        ["NTPC-INS-110", "D/P TRANSMITTER 0-10 BAR 4-20MA HART SMART PRIMARY AIR", "EA", 33500.0, 40.0, "Emerson Process", "90262000"]
    ]

    sail_rows = [
        ["STEEL_MAT_NO", "PRODUCT_SPECIFICATION", "UOM", "PRICE_INR", "REQD_QTY", "SUPPLIER_NAME", "TARIFF_NO"],
        ["SAIL-REF-501", "MAGNESITE CARBON BRICK 100MM LADLE REFRACTORY LINING", "TON", 68000.0, 120.0, "Tata Refractories Ltd", "69021010"],
        ["SAIL-VLV-502", "6\" 300# GATE VALVE FLANGED WCB BLAST FURNACE COOLING WATER", "Numbers", 13800.0, 90.0, "L&T Valves Limited", "84818030"],
        ["SAIL-PIP-503", "PIPE CS SMLS 4\" SCH 40 ASTM A106 GR.B MILL AIR SYSTEM", "MTR", 2490.0, 800.0, "Jindal Saw Ltd", "73041910"],
        ["SAIL-BRG-504", "SPHERICAL ROLLER BEARING 22218 EK/C3 FAG RUNOUT TABLE", "Nos", 8500.0, 110.0, "Schaeffler India", "84823000"],
        ["SAIL-BRG-505", "DEEP GROOVE BALL BEARING 6205-2RS1 SKF MOTOR SPINDLE", "EA", 930.0, 350.0, "SKF India Ltd", "84821010"],
        ["SAIL-OIL-506", "SERVOMESH SP 220 INDUSTRIAL HEAVY GEAR OIL 210L DRUM", "DRM", 42000.0, 85.0, "Indian Oil Corp Ltd", "27101980"],
        ["SAIL-FST-507", "HIGH TENSILE STUD BOLT B7/2H M24 X 160MM ROLLING MILL", "SET", 290.0, 1200.0, "Unbrako Fasteners", "73181500"],
        ["SAIL-ELE-508", "HT ARMORED XLPE CABLE 11KV 3C X 240 SQMM MILL SUBSTATION", "MTR", 1440.0, 1800.0, "Polycab India", "85446090"],
        ["SAIL-ELE-509", "CRANE DUTY SLIP RING MOTOR 45KW 6-POLE 415V FOOT MOUNTED", "EA", 165000.0, 8.0, "BHEL Electricals", "85015290"],
        ["SAIL-INS-510", "OPTICAL PYROMETER NON-CONTACT 400-1400 DEG C 4-20MA", "SET", 92000.0, 15.0, "Land Instruments", "90251990"]
    ]

    bhel_rows = [
        ["PART_IDENTIFIER", "ENGINEERING_SPECIFICATION", "UNIT", "NET_PRICE", "DEMAND", "MANUFACTURER", "HSN_CODE"],
        ["BHEL-GEN-801", "COPPER ROTOR STRIP 45 X 8 MM CDA110 FOR 500MW GENERATOR", "KG", 920.0, 1200.0, "Sterlite Copper", "74071010"],
        ["BHEL-VLV-802", "GLOBE VALVE 2\" 600# FORGED CS A105 SW TURBINE DRAIN", "Nos", 6400.0, 60.0, "Audco India Ltd", "84818030"],
        ["BHEL-PIP-803", "PIPE CS SMLS 4\" SCH 40 ASTM A106 AUXILIARY PIPING", "MTR", 2460.0, 600.0, "Maharashtra Seamless", "73041910"],
        ["BHEL-BRG-804", "TAPER ROLLER BEARING 32214 TIMKEN TURBINE GEARBOX", "EA", 4150.0, 80.0, "Timken India Ltd", "84822000"],
        ["BHEL-BRG-805", "DEEP GROOVE BALL BEARING 6205-2RS1 SKF AUXILIARY MOTOR", "Nos", 915.0, 250.0, "SKF India Ltd", "84821010"],
        ["BHEL-OIL-806", "SHELL OMALA S2 G 220 INDUSTRIAL GEARBOX OIL 209L", "DRM", 45500.0, 30.0, "Shell India", "27101980"],
        ["BHEL-FST-807", "STUD BOLT B7/2H M20 X 120MM CASING MOUNTING", "SET", 188.0, 1400.0, "Sundram Fasteners", "73181500"],
        ["BHEL-ELE-808", "HT 11KV XLPE CABLE 3C X 240 SQMM ALUMINIUM CONDUCTOR", "MTR", 1430.0, 1200.0, "KEI Industries Ltd", "85446090"],
        ["BHEL-ELE-809", "IE3 ENERGY EFFICIENT INDUCTION MOTOR 45KW 4-POLE 415V", "EA", 123000.0, 10.0, "Bharat Bijlee Ltd", "85015290"],
        ["BHEL-INS-810", "SMART PRESSURE TRANSMITTER 0-10 BAR 4-20MA HART", "EA", 33800.0, 30.0, "Yokogawa India", "90262000"]
    ]

    coalindia_rows = [
        ["COAL_ITEM_NO", "MATERIAL_DESCRIPTION", "UOM", "RATE", "QTY", "VENDOR", "HSN"],
        ["CIL-EXC-901", "DRAGLINE BUCKET TOOTH FORGING ALLOY STEEL CASTING 45KG", "Nos", 28000.0, 80.0, "L&T Heavy Engineering", "84314990"],
        ["CIL-PIP-902", "SEAMLESS PIPE CS 4\" SCH 40 ASTM A106 DEWATERING MINE", "MTR", 2480.0, 1200.0, "Jindal Saw Ltd", "73041910"],
        ["CIL-BRG-903", "SPHERICAL ROLLER BEARING 22218 EK/C3 FAG CRUSHER SHAFT", "EA", 8550.0, 70.0, "Schaeffler India", "84823000"],
        ["CIL-BRG-904", "BALL BEARING 6205-2RS1 SKF CONVEYOR ROLLER MOTOR", "Nos", 925.0, 450.0, "SKF India Ltd", "84821010"],
        ["CIL-LUB-905", "HEAVY DUTY MINING GREASE MOBILITH SHC 100 (18KG BUCKET)", "BKT", 13100.0, 50.0, "ExxonMobil India", "27101980"],
        ["CIL-OIL-906", "MAK AMOCAM 220 INDUSTRIAL GEAR OIL 210L DRUM MINING CRUSHER", "DRM", 42500.0, 40.0, "Bharat Petroleum", "27101980"],
        ["CIL-FST-907", "STUD BOLT B7/2H M24 X 160MM HIGH TENSILE CRUSHER CASING", "SET", 295.0, 800.0, "Unbrako Fasteners", "73181500"],
        ["CIL-ELE-908", "FLEXIBLE TRAILING CABLE 3.3KV 3C X 70 SQMM MINING TBM", "MTR", 2800.0, 600.0, "Fort Gloster Cables", "85446090"],
        ["CIL-ELE-909", "FLAMEPROOF EX-D INDUCTION MOTOR 45KW 415V MINING DGMS CERTIFIED", "EA", 185000.0, 6.0, "Kirloskar Electric", "85015290"],
        ["CIL-INS-910", "HEAVY DUTY MINE PRESSURE TRANSMITTER 0-10 BAR 4-20MA INTRINSICALLY SAFE", "EA", 37000.0, 25.0, "Yokogawa India", "90262000"]
    ]

    files_data = {
        "cpcl_materials.csv": {
            "header": ["MATERIAL_NO", "ITEM_SPEC", "UNIT_OF_MEASURE", "LAST_PO_PRICE", "QUANTITY", "VENDOR_NAME", "HSN_CODE"],
            "rows": cpcl_rows
        },
        "iocl_materials.csv": {
            "header": ["SAP_MATNR", "MATERIAL_DESC", "BASE_UOM", "NETPR", "PO_QTY", "VENDOR_NAME", "COMMODITY_CODE"],
            "rows": iocl_rows
        },
        "bpcl_materials.csv": {
            "header": ["ITEM_CODE", "SHORT_TEXT", "UOM", "UNIT_PRICE", "ANNUAL_DEMAND", "SUPPLIER_NAME", "HSN"],
            "rows": bpcl_rows
        },
        "ongc_materials.csv": {
            "header": ongc_rows[0],
            "rows": ongc_rows[1:]
        },
        "ntpc_materials.csv": {
            "header": ntpc_rows[0],
            "rows": ntpc_rows[1:]
        },
        "sail_materials.csv": {
            "header": sail_rows[0],
            "rows": sail_rows[1:]
        },
        "bhel_materials.csv": {
            "header": bhel_rows[0],
            "rows": bhel_rows[1:]
        },
        "coalindia_materials.csv": {
            "header": coalindia_rows[0],
            "rows": coalindia_rows[1:]
        }
    }

    generated_files = []
    for fname, data in files_data.items():
        fpath = os.path.join(output_dir, fname)
        with open(fpath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(data["header"])
            for r in data["rows"]:
                writer.writerow(r)
        generated_files.append(fpath)
        print(f"Generated {fname:24} -> {len(data['rows']):2} rows ({os.path.getsize(fpath)} bytes)")

    # Also generate a bundled zip file for easy one-click download
    zip_path = os.path.join(output_dir, "unimm_all_synthetic_cpse_datasets.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fpath in generated_files:
            zipf.write(fpath, arcname=os.path.basename(fpath))
    print(f"Generated archive {os.path.basename(zip_path):24} ({os.path.getsize(zip_path)} bytes)")

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_dir = os.path.join(base_dir, "data", "synthetic_datasets")
    generate_datasets(out_dir)
