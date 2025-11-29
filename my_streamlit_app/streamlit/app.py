import streamlit as st
import os
import base64
import speech_recognition as sr
from langchain_ollama import ChatOllama
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.embeddings.ollama import OllamaEmbeddings # Ollama Embedding for RAG

# ----------------------------------------------------------------------
# 1. INITIALIZE SESSION STATE
# ----------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "chatbot" 
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "Username": "Guest",
        "Select your category": "General",
        "Language": "English",
        "Exams": "None",
    }
# RAG Components
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

# ----------------------------------------------------------------------
# 2. RAG AND CHAT FUNCTIONS
# ----------------------------------------------------------------------

@st.cache_resource
def get_pdf_processor(pdf_file_path):
    """Loads PDF, splits into chunks, and creates a vector store using Ollama Embeddings."""
    try:
        # 1. Load the PDF
        loader = PyPDFLoader(pdf_file_path)
        documents = loader.load()
        
        # 2. Split the documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3. Create Ollama Embeddings and Chroma Vector Store
        embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434/")
        vectorstore = Chroma.from_documents(chunks, embeddings)
        
        return vectorstore
    except Exception as e:
        st.error(f"Error processing PDF. Ensure 'nomic-embed-text' is running on Ollama: {e}")
        return None

def get_rag_response(question, vectorstore):
    """Uses the vector store and LLM to answer the question based on the document."""
    try:
        model = ChatOllama(model="llama3.2:1b", base_url="http://localhost:11434/")
        retriever = vectorstore.as_retriever()
        
        # Format chat history for the chain
        chat_history = []
        for msg in st.session_state.conversation:
            if "user" in msg:
                chat_history.append(HumanMessage(content=msg["user"]))
            if "bot" in msg:
                chat_history.append(SystemMessage(content=msg["bot"]))

        # Define the System Prompt to enforce RAG behavior
        rag_prompt = f"""
        You are 'SWADESH', an AI assistant specialized in analyzing the provided document.
        Answer the user's question based ONLY on the context provided in the retrieved document chunks.
        Do not use external knowledge.
        If you cannot find the answer in the document, state clearly that the information is not available in the provided context.
        """
        
        # Creating the Conversational Retrieval Chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=model,
            retriever=retriever,
            return_source_documents=False,
            # We enforce the custom RAG prompt within the chain using `combine_docs_chain_kwargs`
            # Note: This requires a custom prompt template in a more complex setup, but 
            # for this simple setup, we'll rely on the model's instruction following and context.
            # Using simple 'stuff' combine_docs_chain for simplicity:
            # combine_docs_chain_kwargs={'prompt': ChatPromptTemplate.from_messages([SystemMessage(content=rag_prompt)])}
        )

        result = qa_chain.invoke({"question": question, "chat_history": chat_history})
        return result['answer']
    except Exception as e:
        return f"RAG Error: {e}. Check LLM model 'llama3.2:1b' status."

def generate_response(input_text):
    """Decides between RAG mode and General Chat mode."""
    if st.session_state.vectorstore:
        # RAG Mode
        return get_rag_response(input_text, st.session_state.vectorstore)
    else:
        # General Chat Mode
        user_data = st.session_state.user_data
        model = ChatOllama(model="llama3.2:1b", base_url="http://localhost:11434/")
        try:
            language_instruction = ""
            if user_data['Language'] == "Hindi":
                language_instruction = "Reply only in Hindi."
            elif user_data['Language'] == "English":
                language_instruction = "Reply only in English."

            swadesh_prompt = f"""
            You are 'SWADESH', an AI assistant. You are in General Chat mode.
            The user's name is {user_data['Username']}, and their Category of interest is '{user_data['Select your category']}'.
            {language_instruction}
            New question: {input_text}
            """
            response = model.invoke(swadesh_prompt)
            return getattr(response, "content", str(response))
        except Exception as e:
            return f"General Chat Error: {e}. Check LLM model 'llama3.2:1b' status."

# ----------------------------------------------------------------------
# 3. UI HELPER FUNCTIONS
# ----------------------------------------------------------------------

def set_background(image_file):
    """Sets the background of a Streamlit app to a local image."""
    try:
        # Check if the file exists before opening
        if not os.path.exists(image_file):
             # st.error(f"Background image file not found: {image_file}")
             return # Skip setting background if file is missing

        with open(image_file, "rb") as f:
            img_data = f.read()
        b64_encoded = base64.b64encode(img_data).decode()
        style = f"""
            <style>
            .stApp {{
                background-image: url(data:image/png;base64,{b64_encoded});
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
        """
        st.markdown(style, unsafe_allow_html=True)
    except Exception as e:
        # st.error(f"Error setting background: {e}")
        pass # Silently fail if there's a file access issue

# ----------------------------------------------------------------------
# 4. CHATBOT PAGE UI
# ----------------------------------------------------------------------

def chatbot_page():
    # --- UI Setup ---
    set_background("image1.jpg") # Ensure 'image1.jpg' is in the same directory
    
    # Custom CSS for fixing chat history display issues (optional but good practice)
    st.markdown("""
        <style>
        /* Fix for chat bubbles in narrow columns */
        .stChatMessage {
            clear: both;
            overflow: hidden;
            display: block;
            width: 100%;
        }
        /* Streamlit main content padding */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        st.image("logo1.png", width=500) # Ensure 'logo1.png' is in the same directory
    
    mode_text = f"Current Mode: {'RAG (Chatting with ' + st.session_state.uploaded_filename + ')' if st.session_state.vectorstore else 'General Chat'}"
    
    st.markdown(
        f"""
        <h2 style='text-align:center; color:#FFFFFF; font-family:Arial Black;'>Hello! I'm <span style='color:#00FFE5;'>Swadesh</span>. 
        <br><span style='font-size:16px; color:#A9A9A9;'>{mode_text}</span>
        </h2>
        """, unsafe_allow_html=True
    )
    
    # --- PDF Uploader Section ---
    st.markdown("<hr style='border:1px solid #00FFE5'>", unsafe_allow_html=True)
    st.markdown("#### 📄 Document Analysis (RAG)", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload a PDF to chat with the document", type="pdf", key="pdf_uploader")
    
    if uploaded_file:
        # Check if a new file or a different file is uploaded
        if st.session_state.uploaded_filename != uploaded_file.name:
            # 1. Save the uploaded file temporarily
            temp_file_path = uploaded_file.name
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 2. Process the PDF
            with st.spinner(f"Processing '{uploaded_file.name}'... This may take a moment."):
                vectorstore = get_pdf_processor(temp_file_path)
                
            # 3. Update session state
            if vectorstore:
                st.session_state.vectorstore = vectorstore
                st.session_state.pdf_processed = True
                st.session_state.conversation = [] # Clear chat history for new document
                st.session_state.uploaded_filename = uploaded_file.name
                st.success(f"PDF '{uploaded_file.name}' processed successfully! Ask questions about it below.")
            else:
                st.error("Could not process PDF. Please check Ollama server status.")
    
    # --- Chat History Display ---
    st.markdown("<hr style='border:1px solid #00FFE5'>", unsafe_allow_html=True)

    for message in st.session_state.conversation:
        if "user" in message:
            st.markdown(f"""
                <div style="
                    text-align:right;
                    background: linear-gradient(90deg,#18FFFF,#00BCD4);
                    color:#000;
                    padding:12px;
                    border-radius:15px;
                    margin-bottom:5px;
                    max-width:75%;
                    float:right;
                    clear:both;">
                    <strong>You:</strong> {message["user"]}
                </div>
            """, unsafe_allow_html=True)
        if "bot" in message:
            st.markdown(f"""
                <div style="
                    text-align:left;
                    background: linear-gradient(90deg,#fff,#e0f7fa);
                    color:#000;
                    padding:12px;
                    border-radius:15px;
                    margin-bottom:10px;
                    max-width:75%;
                    float:left;
                    clear:both;">
                    <strong>Bot:</strong> {message["bot"]}
                </div>
            """, unsafe_allow_html=True)
    
    # --- Input and Voice Section ---
    st.markdown("<hr style='border:1px solid #00FFE5'>", unsafe_allow_html=True)

    # Voice input section
    st.markdown("#### 🎙 Speak to Swadesh", unsafe_allow_html=True)
    if st.button("Start Voice Recording", key="voice"):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                st.info("🎤 Listening... Speak now.")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

            lang_map = {"English": "en-IN", "Hindi": "hi-IN"}
            voice_text = recognizer.recognize_google(audio, language=lang_map.get(st.session_state.user_data["Language"], "en-IN"))
            st.success(f"Recognized: {voice_text}")
            
            with st.spinner("Generating response..."):
                response = generate_response(voice_text)
                st.session_state.conversation.append({"user": voice_text, "bot": response})
            st.rerun()
        except sr.WaitTimeoutError:
            st.warning("No speech detected. Please try again.")
        except sr.UnknownValueError:
            st.warning("Could not understand audio.")
        except Exception as mic_err:
            st.error(f"🎙 Microphone error: {mic_err}. Check if microphone is connected and operational.")

    # Text input
    with st.form("llm-form", clear_on_submit=True):
        text = st.text_area("Type your message...", placeholder="Type something here...", height=80)
        submit = st.form_submit_button("Send", use_container_width=True)
        
    if submit and text:
        with st.spinner("Generating response..."):
            response = generate_response(text)
            st.session_state.conversation.append({"user": text, "bot": response})
        st.rerun()

    # --- Bottom navigation buttons ---
    col1, col2, col3 = st.columns(3)
    with col1:
        # Link to external Flask app or main page (adjust URL if needed)
        st.link_button("⬅️ Back to Home", url="http://127.0.0.1:5001") 
    with col2:
        if st.button("🧹 Clean Chat History", use_container_width=True):
            st.session_state.conversation = []; st.rerun()
    with col3:
        if st.session_state.vectorstore:
            # Button to exit RAG mode
            if st.button("❌ Exit Document Chat", use_container_width=True):
                st.session_state.vectorstore = None
                st.session_state.pdf_processed = False
                st.session_state.uploaded_filename = None
                st.session_state.conversation = []
                st.success("Switched back to General Chat Mode.")
                st.rerun()

# ----------------------------------------------------------------------
# 5. ROUTER (Main Execution)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    chatbot_page()