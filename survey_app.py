
                            placeholder=f"Example: The {ML_MODELS[model_type]['name']} achieved 85% accuracy. Q1 (content) was the most important feature, followed by Q2 (instructor). This suggests..."
                        )
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if st.button("💾 Save Interpretation", key='save_ml', type="primary"):
                                if ml_interpretation.strip():
                                    save_interpretation(f'ml_{model_type}', ml_interpretation)
                                    st.success("✓ Interpretation saved! Scroll to see it above.")
                                    st.balloons()
                                    st.rerun()  # Refresh to show in "Previous Interpretations"
                                else:
                                    st.warning("⚠️ Please write an interpretation first!")
                        
                        with col2:
                            if ml_interpretation.strip():
                                word_count = len(ml_interpretation.split())
                                st.caption(f"📝 {word_count} words")
            
            # Always show ML interpretation history at bottom
            st.markdown("---")
            st.markdown("### 📚 All ML Interpretation History")
            
            # Get all ML interpretations
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT analysis_type, interpretation, timestamp FROM interpretations WHERE analysis_type LIKE 'ml_%' ORDER BY timestamp DESC")
            all_ml_interps = c.fetchall()
            conn.close()
            
            if all_ml_interps:
                st.success(f"✅ {len(all_ml_interps)} ML interpretation(s) saved across all models")
                
                for idx, (analysis_type, interp, timestamp) in enumerate(all_ml_interps):
                    model_key = analysis_type.replace('ml_', '')
                    model_name = ML_MODELS.get(model_key, {}).get('name', model_key)
                    
                    with st.container():
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.markdown(f"**🤖 {model_name}** - {timestamp}")
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_ml_{idx}"):
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("DELETE FROM interpretations WHERE analysis_type=? AND timestamp=?", 
                                         (analysis_type, timestamp))
                                conn.commit()
                                conn.close()
                                st.rerun()
                        
                        st.info(interp)
                        if idx < len(all_ml_interps) - 1:
                            st.markdown("---")
            else:
                st.info("💡 No saved ML interpretations yet. Train models and save your interpretations above!")

# ============================================================================
# SURVEY PAGE
# ============================================================================

def survey_page():
    """Main survey interface"""
    survey_title = get_setting('survey_title', 'Touchless Satisfaction Survey')
    st.title(f"✋ {survey_title}")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        **Gesture Guide:**
        
        ❤️ Heart = Very Satisfied (5)
        👍 Thumbs Up = Satisfied (4)  
        👎 Thumbs Down = Unsatisfied (2)
        ☝️ Waving = Very Unsatisfied (1)
        ✊ Fist = No Answer
        """)
        
        st.info("Show clear hand gestures for best results!")
    
    # Initialize session
    if 'started' not in st.session_state:
        st.session_state.started = False
        st.session_state.current_q = 0
        st.session_state.responses = []
        st.session_state.completed = False
    
    # Start screen
    if not st.session_state.started:
        st.markdown("## Welcome!")
        st.markdown("Please provide your information to begin the survey.")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your Name:")
        with col2:
            org = st.text_input("Organization:")
        
        if st.button("🚀 Start Survey", type="primary"):
            st.session_state.name = name or "Anonymous"
            st.session_state.org = org or "N/A"
            st.session_state.started = True
            st.rerun()
        return
    
    # Completed screen
    if st.session_state.completed:
        st.success("✅ Survey Complete!")
        st.balloons()
        
        st.markdown("## Your Responses")
        
        df = pd.DataFrame([{
            'Question': f"Q{i+1}",
            'Response': r['label'],
            'Score': r['score'] or 'N/A',
            'Confidence': f"{r['confidence']:.1%}"
        } for i, r in enumerate(st.session_state.responses)])
        
        st.dataframe(df, use_container_width=True)
        
        scores = [r['score'] for r in st.session_state.responses if r['score']]
        if scores:
            avg_score = sum(scores)/len(scores)
            st.metric("Your Average Score", f"{avg_score:.2f}/5.0")
            
            if avg_score >= 4:
                st.success("🎉 Thank you for your positive feedback!")
            elif avg_score >= 3:
                st.info("👍 Thank you for your feedback!")
            else:
                st.warning("We appreciate your honest feedback and will work to improve!")
        
        if st.button("📝 Submit Another Response"):
            st.session_state.started = False
            st.session_state.current_q = 0
            st.session_state.responses = []
            st.session_state.completed = False
            st.rerun()
        return
    
    # Survey in progress
    current_q = st.session_state.current_q
    total_q = len(SURVEY_QUESTIONS)
    
    st.progress(current_q / total_q, text=f"Question {current_q + 1} of {total_q}")
    
    st.markdown(f"## Question {current_q + 1}")
    st.markdown(f"### {SURVEY_QUESTIONS[current_q]}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        img_file = st.camera_input("Show your gesture", key=f"cam_{current_q}")
        
        if img_file:
            image = Image.open(img_file)
            
            with st.spinner("Analyzing gesture..."):
                gesture, confidence = simple_predict(image)
            
            info = GESTURE_MAP[gesture]
            
            st.success(f"Detected: {info['emoji']} {info['label']}")
            st.info(f"Confidence: {confidence:.1%}")
            
            if st.button("✅ Confirm", type="primary"):
                st.session_state.responses.append({
                    'label': info['label'],
                    'score': info['score'],
                    'confidence': confidence
                })
                
                if current_q < total_q - 1:
                    st.session_state.current_q += 1
                    st.rerun()
                else:
                    st.session_state.completed = True
                    
                    # Save to database
                    save_response(
                        st.session_state.name,
                        st.session_state.org,
                        st.session_state.responses
                    )
                    
                    st.rerun()
    
    with col2:
        st.markdown("**Gestures:**")
        for g, info in GESTURE_MAP.items():
            st.write(f"{info['emoji']} {info['label']}")

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Initialize database
    init_database()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("---")
        page = st.radio(
            "Navigation",
            ["📝 Survey", "🔧 Admin Panel"],
            label_visibility="collapsed"
        )
    
    # Route to appropriate page
    if page == "📝 Survey":
        survey_page()
    else:
        admin_panel()

if __name__ == "__main__":
    main()
