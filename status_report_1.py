import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
import pandas as pd

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("MODEL", "gemini-3.5-flash-lite")

st.title("🤖 AI Agent At Your Service 🤖")
#st.markdown("I am here to collect your daily status report")

# Define Schema for Extraction
class StatusReport(BaseModel):
    tester_name: str = Field(description="Name of the tester")
    date: str = Field(description="Date of the report")
    activities_performed: str = Field(description="Summary of activities done")
    test_cases_executed: int = Field(description="Number of test cases executed")
    defects_logged: int = Field(description="Number of defects logged")

system_instruction = """
You are a QA Status Bot collecting daily status reports.
Required Fields:
1. Name of the tester
2. Date
3. Activities Performed
4. Number of Test Cases Executed
5. Number of Defects Logged

Your Goal:
- Check if all 5 fields are present in the conversation.
- If ANY field is missing, ask follow-up questions ONE AT A TIME for only the missing details.
- Once ALL 5 fields are successfully collected, explicitly state: "Report complete and logged successfully!"
"""

# Initialize Gemini Client in session state
if "client" not in st.session_state:
    st.session_state.client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            client_args={"verify": False}, async_client_args={"verify": False}
        ),
    )

# Initialize Chat Session in session state
if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2
        )
    )

# Initialize message history for UI rendering
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": """
        Please provide your daily status report with the following details:
1. Name of the tester
2. Date
3. Activities Performed
4. Number of Test Cases Executed
5. Number of Defects Logged

**Example:**
> 🪷 My name is Jane Doe. On 19-Oct-2025, I tested the Mobile App functionality and executed 25 test cases and logged 2 defects.
"""
    }]

# Display prior chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capture user chat input
if user_input := st.chat_input("Type your status here..."):
    # Display user message
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Send message to Gemini chat session
    response = st.session_state.chat.send_message(user_input)
    bot_response = response.text

    # Display bot response
    with st.chat_message("assistant"):
        st.markdown(bot_response)
    st.session_state.messages.append({"role": "assistant", "content": bot_response})

    # Check if report is complete
    # Check if report is complete
    if "report complete" in bot_response.lower():
        st.success("All details captured!")
        
        # 1. Extract structured JSON from Gemini
        final_response = st.session_state.chat.send_message(
            "Extract the final status report into the structured JSON format.",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StatusReport,
            )
        )
        
        # Parse the JSON response
        report_data = json.loads(final_response.text)
        
        # 2. Convert extracted data into a pandas DataFrame
        df_new = pd.DataFrame([report_data])
        
        excel_file = "qa_status_reports.xlsx"
        
        # 3. Append to existing Excel file or create a new one
        if os.path.exists(excel_file):
            df_existing = pd.read_excel(excel_file)
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_updated = df_new
            
        # Save to local Excel file on the server
        df_updated.to_excel(excel_file, index=False)
        
        st.subheader("--- Final Captured Report ---")
        st.dataframe(df_new) # Displays a clean table in Streamlit
        
        # 4. Provide a download button for the user
        with open(excel_file, "rb") as file:
            st.download_button(
                label="📥 Download Updated Excel Report",
                data=file,
                file_name="qa_status_reports.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )