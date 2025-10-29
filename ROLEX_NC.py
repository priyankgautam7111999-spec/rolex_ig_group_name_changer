#!/usr/bin/env python3
"""
Instagram Group Name Changer - GUI (Selenium + Tkinter)

Run:
  python bot_gui.py

Main GUI script. Includes:
- login (2FA prompt), thread selection, delay popups (after login and after group select),
- single-name / multi-name emoji rotation, per-second countdown, live stats,
- fullscreen ROLEX banner on login with subtitle.
"""
import threading
import queue
import time
import random
import json
import sys
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import tkinter.font as tkfont

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DEFAULT_EMOJIS = [
    "😂","🤣","😍","🥰","😘","😎","🤩","😅","😊","👍",
    "🔥","✨","🎉","🎊","💥","💫","🌟","💖","💯","🤖",
    "🦄","🍀","🌈","🍕","🍩","☕","🍻","🎧","📸","🎬",
    "⚡","🔔","🔒","🎯","🏆","🥇","💡","📣","🧩","🔮",
    "🌙","☀️","⭐","💌","🎵","🎶","🌺","🌸","🌼","🍃"
]

# Queues for thread communication
gui_q = queue.Queue()   # selenium -> gui messages
cmd_q = queue.Queue()   # gui -> selenium commands

# Thread safe flag to stop background worker
stop_event = threading.Event()


def start_driver(headless: bool = False):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1200,900")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.maximize_window()
    except Exception:
        pass
    return driver


def wait_for(driver, timeout=15):
    return WebDriverWait(driver, timeout)


def log(msg: str):
    gui_q.put({"type": "log", "msg": msg})


def selenium_worker(username: str, password: str, headless: bool,
                    emojis: List[str], base_names: List[str], interval: int,
                    count: int, random_mode: bool, mode: str, single_name_mode: bool):
    """
    Background thread running Selenium. Communicates with GUI.
    Sends messages via gui_q with types: log, 2fa_request, threads, login_success,
    countdown, stats, error.
    """
    driver = None
    try:
        driver = start_driver(headless=headless)
        log("[+] Browser started. Opening Instagram login...")

        # Open login page
        driver.get("https://www.instagram.com/accounts/login/")
        w = wait_for(driver, 20)

        # Accept cookie if present
        try:
            w.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Only allow essential') or contains(text(),'Accept all') or contains(text(),'Accept')]"))).click()
            log("[*] Cookie dialog accepted (if present).")
        except Exception:
            pass

        # Fill in credentials
        try:
            w.until(EC.presence_of_element_located((By.NAME, "username")))
            user_in = driver.find_element(By.NAME, "username")
            pass_in = driver.find_element(By.NAME, "password")
            user_in.clear()
            user_in.send_keys(username)
            pass_in.clear()
            pass_in.send_keys(password)
            pass_in.send_keys(Keys.ENTER)
            log("[*] Submitted credentials. Waiting for login or challenge...")
        except Exception as e:
            log(f"[!] Could not find login fields: {e}")
            gui_q.put({"type": "login_failed"})
            return

        # Wait for login or 2FA
        time.sleep(2)
        for _ in range(60):
            if stop_event.is_set():
                log("[*] Stop requested during login wait.")
                return
            try:
                code_inputs = driver.find_elements(By.NAME, "verificationCode")
                if code_inputs:
                    log("[!] 2FA detected. Requesting code via GUI.")
                    gui_q.put({"type": "2fa_request"})
                    code = None
                    while True:
                        try:
                            cmd = cmd_q.get(timeout=0.5)
                            if cmd.get("cmd") == "send_2fa":
                                code = cmd.get("code")
                                break
                            elif cmd.get("cmd") == "abort":
                                log("[*] Aborted by user from GUI.")
                                return
                        except queue.Empty:
                            if stop_event.is_set():
                                return
                            continue
                    if code:
                        try:
                            code_inputs[0].send_keys(code)
                            code_inputs[0].send_keys(Keys.ENTER)
                            log("[*] 2FA code submitted. Waiting for completion...")
                        except Exception as e:
                            log(f"[!] Failed to submit 2FA code: {e}")
                    break
            except Exception:
                pass

            # logged-in indicator
            try:
                if driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Home'], svg[aria-label='Messenger'], a[href='/direct/inbox/']"):
                    log("[+] Login appears successful.")
                    break
            except Exception:
                pass
            time.sleep(0.5)

        # dismiss save dialogs
        time.sleep(1)
        for xpath in ["//button[contains(text(), 'Not Now')]", "//button[contains(text(), 'Save Info')]", "//button[contains(text(),'Not Now')]"]:
            try:
                el = driver.find_element(By.XPATH, xpath)
                el.click()
                time.sleep(0.3)
            except Exception:
                pass

        # open inbox & scrape threads
        driver.get("https://www.instagram.com/direct/inbox/")
        try:
            wait_for(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@role,'navigation') or contains(@role,'list')]")))
        except Exception:
            log("[!] Inbox load may have issues; continuing.")
        time.sleep(1)

        candidates = []
        try:
            elems = driver.find_elements(By.XPATH, "//div[(contains(@role,'button') or contains(@role,'link') or contains(@role,'article')) and string-length(normalize-space(.))>0]")
            seen = set()
            for e in elems:
                try:
                    txt = e.text.strip()
                    if not txt:
                        continue
                    label = txt.splitlines()[0]
                    if label in seen:
                        continue
                    seen.add(label)
                    candidates.append({"label": label, "raw": txt})
                    if len(candidates) >= 40:
                        break
                except Exception:
                    continue
        except Exception as e:
            log(f"[!] Error scraping threads: {e}")

        gui_q.put({"type": "login_success"})
        if candidates:
            gui_q.put({"type": "threads", "data": candidates})
            log(f"[*] Found {len(candidates)} candidate threads.")
        else:
            log("[!] No threads found automatically.")

        # main command loop
        selected_thread_idx = None
        while True:
            if stop_event.is_set():
                log("[*] Stop requested; ending worker loop.")
                return
            try:
                cmd = cmd_q.get(timeout=0.5)
            except queue.Empty:
                continue

            if cmd.get("cmd") == "refresh_threads":
                log("[*] Refreshing thread list...")
                candidates = []
                try:
                    elems = driver.find_elements(By.XPATH, "//div[(contains(@role,'button') or contains(@role,'link') or contains(@role,'article')) and string-length(normalize-space(.))>0]")
                    seen = set()
                    for e in elems:
                        try:
                            txt = e.text.strip()
                            if not txt:
                                continue
                            label = txt.splitlines()[0]
                            if label in seen:
                                continue
                            seen.add(label)
                            candidates.append({"label": label, "raw": txt})
                            if len(candidates) >= 40:
                                break
                        except Exception:
                            continue
                except Exception as e:
                    log(f"[!] Error while refreshing threads: {e}")
                gui_q.put({"type": "threads", "data": candidates})
                continue

            if cmd.get("cmd") == "select_thread":
                idx = cmd.get("index")
                log(f"[*] select_thread index={idx}")
                try:
                    elems = driver.find_elements(By.XPATH, "//div[(contains(@role,'button') or contains(@role,'link') or contains(@role,'article')) and string-length(normalize-space(.))>0]")
                    if 0 <= idx < len(elems):
                        driver.execute_script("arguments[0].scrollIntoView(true);", elems[idx])
                        time.sleep(0.2)
                        elems[idx].click()
                        time.sleep(1)
                        log("[+] Thread opened in browser.")
                    else:
                        log("[!] Selected index out of bounds.")
                except Exception as e:
                    log(f"[!] Error opening thread: {e}")
                continue

            if cmd.get("cmd") == "start_rotation":
                params = cmd.get("params", {})
                provided_base_names = params.get("base_names", [])
                emoji_list = params.get("emojis", [])
                requested_count = params.get("count", 0)
                req_interval = max(1, params.get("interval", 60))
                random_mode_local = params.get("random", False)
                mode_local = params.get("mode", "end")
                single_name_local = bool(params.get("single_name_mode", True))

                if single_name_local:
                    base_single = provided_base_names[0] if provided_base_names else "Group"
                    base_total = 1
                else:
                    base_list = provided_base_names
                    base_total = len(base_list)

                emoji_total = len(emoji_list)
                emoji_idx = 0
                base_idx = 0
                performed = 0

                gui_q.put({"type": "stats", "performed": performed, "current_emoji": "", "emoji_index": 0, "emoji_total": emoji_total,
                            "current_base": (base_single if single_name_local else (base_list[0] if base_total>0 else "")),
                            "base_index": 1, "base_total": base_total})

                # rotation loop
                while True:
                    if stop_event.is_set():
                        gui_q.put({"type": "countdown", "remaining": -1})
                        return
                    if requested_count and performed >= requested_count:
                        gui_q.put({"type": "countdown", "remaining": -1})
                        break

                    if single_name_local:
                        current_base = base_single
                        current_base_index = 1
                    else:
                        current_base = base_list[base_idx % base_total]
                        current_base_index = (base_idx % base_total) + 1

                    if random_mode_local:
                        emoji = random.choice(emoji_list)
                        emoji_index_for_ui = 0
                    else:
                        emoji = emoji_list[emoji_idx % emoji_total]
                        emoji_index_for_ui = (emoji_idx % emoji_total) + 1

                    if mode_local == "start":
                        new_name = f"{emoji} {current_base}"
                    elif mode_local == "both":
                        new_name = f"{emoji} {current_base} {emoji}"
                    elif mode_local == "between":
                        parts = current_base.split()
                        new_name = f" {emoji} ".join(parts) if len(parts) >= 2 else f"{current_base} {emoji}"
                    else:
                        new_name = f"{current_base} {emoji}"

                    changed = False
                    try:
                        # try open details pane
                        try:
                            btn = driver.find_element(By.XPATH, "//button//*[name()='svg' and (contains(@aria-label,'Details') or contains(@aria-label,'Conversation details') or contains(@aria-label,'More') or contains(@aria-label,'Info'))]/ancestor::button")
                            btn.click()
                            time.sleep(0.6)
                        except Exception:
                            try:
                                btn2 = driver.find_element(By.XPATH, "//button[contains(@aria-label,'Conversation details') or contains(@aria-label,'Details') or contains(@aria-label,'More actions')]")
                                btn2.click()
                                time.sleep(0.6)
                            except Exception:
                                try:
                                    header = driver.find_element(By.XPATH, "//header//div[.//span] | //div[contains(@role,'toolbar')]")
                                    header.click()
                                    time.sleep(0.6)
                                except Exception:
                                    pass

                        tries = [
                            "//input[@placeholder='Name']",
                            "//input[@name='name']",
                            "//input[contains(@aria-label,'Name')]",
                            "//div[@contenteditable='true']",
                            "//textarea[@placeholder='Name']",
                            "//input"
                        ]
                        for xp in tries:
                            try:
                                inputs = driver.find_elements(By.XPATH, xp)
                                for inp in inputs:
                                    try:
                                        if not inp.is_displayed():
                                            continue
                                        try:
                                            inp.click()
                                        except Exception:
                                            pass
                                        try:
                                            inp.clear()
                                        except Exception:
                                            driver.execute_script("arguments[0].innerText='';", inp)
                                        time.sleep(0.2)
                                        inp.send_keys(new_name)
                                        time.sleep(0.3)
                                        inp.send_keys(Keys.ENTER)
                                        time.sleep(1)
                                        changed = True
                                        break
                                    except Exception:
                                        continue
                                if changed:
                                    break
                            except Exception:
                                continue

                        if not changed:
                            try:
                                btn = driver.find_element(By.XPATH, "//button[contains(., 'Change Name') or contains(., 'Edit Name') or contains(., 'Rename')]")
                                btn.click()
                                time.sleep(0.4)
                                for xp in tries:
                                    try:
                                        inputs = driver.find_elements(By.XPATH, xp)
                                        for inp in inputs:
                                            try:
                                                if not inp.is_displayed():
                                                    continue
                                                try:
                                                    inp.click()
                                                except Exception:
                                                    pass
                                                try:
                                                    inp.clear()
                                                except Exception:
                                                    driver.execute_script("arguments[0].innerText='';", inp)
                                                time.sleep(0.2)
                                                inp.send_keys(new_name)
                                                time.sleep(0.3)
                                                inp.send_keys(Keys.ENTER)
                                                time.sleep(0.8)
                                                changed = True
                                                break
                                            except Exception:
                                                continue
                                        if changed:
                                            break
                                    except Exception:
                                        continue
                            except Exception:
                                pass

                        if changed:
                            performed += 1
                            log(f"[+] ({performed}) Set name -> {new_name}")
                            gui_q.put({"type": "stats", "performed": performed, "current_emoji": emoji,
                                        "emoji_index": emoji_index_for_ui, "emoji_total": emoji_total,
                                        "current_base": current_base, "base_index": current_base_index, "base_total": base_total})
                        else:
                            log("[!] Could not locate editable name field. Please open thread details manually and edit once to ensure UI state.")

                    except Exception as e:
                        log(f"[!] Exception while changing name: {e}")

                    emoji_idx += 1
                    if not single_name_local:
                        if (emoji_idx % emoji_total) == 0:
                            base_idx += 1

                    # Sleep with per-second countdown
                    jitter = random.uniform(0.05, 0.2) * req_interval
                    sleep_time = req_interval + jitter
                    if sleep_time < 1:
                        sleep_time = max(sleep_time, 1)

                    remaining = int(sleep_time)
                    gui_q.put({"type": "countdown", "remaining": remaining})
                    log(f"[*] Sleeping ~{int(sleep_time)}s before next change.")

                    slept = 0.0
                    while slept < sleep_time:
                        if stop_event.is_set():
                            gui_q.put({"type": "countdown", "remaining": -1})
                            gui_q.put({"typ
