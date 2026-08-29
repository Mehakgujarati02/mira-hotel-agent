"""
MIRA - AI Hospitality Assistant
Streamlit front-end.

This file ONLY renders the UI and talks to the existing
MiraAgent.process_message() interface. No backend logic
(intent extraction, search, selection, booking, dates) is
duplicated or modified here.
"""

import os
import sys

import streamlit as st

# ------------------------------------------------------------------
# Make the existing agent/ package importable.
# agent/agent.py itself uses plain imports like `from state import
# GuestState`, so agent/ needs to be on sys.path (not just the
# project root) for those internal imports to resolve.
# ------------------------------------------------------------------

AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent")

if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from agent import MiraAgent  # noqa: E402  (import after sys.path setup)


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="MIRA - AI Hospitality Assistant",
    page_icon="🏨",
    layout="wide",
)


# ==========================================================
# SESSION STATE INITIALISATION
# ==========================================================

def start_new_conversation():
    st.session_state.mira = MiraAgent()
    st.session_state.messages = []


if "mira" not in st.session_state:
    start_new_conversation()


# ==========================================================
# SIDEBAR - BOOKING DETAILS
# ==========================================================

def render_sidebar():
    with st.sidebar:
        st.header("Booking Details")

        state = st.session_state.mira.state.summary()

        st.markdown(f"**Destination:** {state['destination'] or '-'}")
        st.markdown(f"**Guests:** {state['guests'] or '-'}")
        st.markdown(f"**Rooms:** {state['rooms'] or '-'}")

        budget = state["budget"]
        st.markdown(f"**Budget:** {'₹' + format(budget, ',') if budget else '-'}")

        preferences = state["preferences"]
        st.markdown(f"**Preferences:** {', '.join(preferences) if preferences else '-'}")

        st.markdown(f"**Selected Hotel:** {state['selected_hotel'] or '-'}")
        st.markdown(f"**Selected Room:** {state['selected_room'] or '-'}")

        st.divider()

        st.markdown(f"**Booking Status:** `{state['booking_status']}`")

        st.divider()

        if st.button("🔄 New Conversation", use_container_width=True):
            start_new_conversation()
            st.rerun()


# ==========================================================
# HEADER
# ==========================================================

st.title("🏨 MIRA")
st.caption("AI Hospitality Assistant")
st.write("How can I help you find your perfect stay?")

render_sidebar()


# ==========================================================
# CHAT HISTORY
# ==========================================================

for entry in st.session_state.messages:
    with st.chat_message(entry["role"]):
        st.write(entry["content"])


# ==========================================================
# CHAT INPUT
# ==========================================================

user_message = st.chat_input("Type your message...")

if user_message:

    st.session_state.messages.append({"role": "user", "content": user_message})

    with st.chat_message("user"):
        st.write(user_message)

    try:
        response = st.session_state.mira.process_message(user_message)
        reply_text = response.get("message", "Sorry, I didn't understand that.")

    except Exception as error:
        reply_text = (
            "Something went wrong on my end while processing that. "
            "Could you try rephrasing, or start a new conversation?"
        )
        st.error(f"Internal error: {error}")

    st.session_state.messages.append({"role": "assistant", "content": reply_text})

    with st.chat_message("assistant"):
        st.write(reply_text)

    # Sidebar reflects the latest state after every message.
    st.rerun()