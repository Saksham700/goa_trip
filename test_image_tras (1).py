import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import requests

st.set_page_config(
    page_title="Goa Trip Dashboard 🏖️",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

GOOGLE_AI_API_KEY = "AIzaSyCfSrrQjzlxKKBQFGuDH_FcwlT1TiX-KVA"
GOOGLE_AI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_AI_API_KEY}"

FRIENDS = ["kattu", "lord", "iyer", "fluffy", "chiknu", "saky"]

EXPENSES_FILE = "expenses.json"
PLANS_FILE = "plans.json"
PAYMENTS_FILE = "payments.json"

def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def initialize_session_state():
    if 'expenses' not in st.session_state:
        st.session_state.expenses = load_data(EXPENSES_FILE)
    if 'plans' not in st.session_state:
        st.session_state.plans = load_data(PLANS_FILE)
    if 'payments' not in st.session_state:
        st.session_state.payments = load_data(PAYMENTS_FILE)

def calculate_balances():
    balances = {friend: 0 for friend in FRIENDS}
    for expense in st.session_state.expenses:
        amount_per_person = expense['amount'] / len(expense['split_between'])
        balances[expense['paid_by']] += expense['amount'] - amount_per_person
        for person in expense['split_between']:
            if person != expense['paid_by']:
                balances[person] -= amount_per_person
    for payment in st.session_state.payments:
        balances[payment['from']] += payment['amount']
        balances[payment['to']] -= payment['amount']    
    return balances

def add_expense():
    with st.form("add_expense_form"):
        st.subheader("➕ Add New Expense")     
        col1, col2 = st.columns(2)      
        with col1:
            description = st.text_input("Expense Description", placeholder="e.g., Dinner at beach restaurant")
            amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
            paid_by = st.selectbox("Paid By", FRIENDS)     
        with col2:
            split_between = st.multiselect("Split Between", FRIENDS, default=FRIENDS)
            category = st.selectbox("Category", ["Food", "Transport", "Accommodation", "Activities", "Shopping", "Other"])
            expense_date = st.date_input("Date", value=date.today())     
        submitted = st.form_submit_button("Add Expense", type="primary")    
        if submitted:
            if description and amount > 0 and split_between:
                new_expense = {
                    'id': len(st.session_state.expenses) + 1,
                    'description': description,
                    'amount': amount,
                    'paid_by': paid_by,
                    'split_between': split_between,
                    'category': category,
                    'date': expense_date.isoformat(),
                    'created_at': datetime.now().isoformat()
                }
                
                st.session_state.expenses.append(new_expense)
                save_data(st.session_state.expenses, EXPENSES_FILE)
                st.success(f"✅ Added expense: {description} - ₹{amount}")
                st.rerun()
            else:
                st.error("Please fill all required fields")

def show_expenses():
    if not st.session_state.expenses:
        st.info("No expenses added yet. Add your first expense above!")
        return
    df = pd.DataFrame(st.session_state.expenses)
    df['date'] = pd.to_datetime(df['date'])    
    col1, col2 = st.columns([2, 1])    
    with col1:
        st.subheader("💰 Recent Expenses")
        for expense in reversed(st.session_state.expenses[-10:]):  # Show last 10
            with st.container():
                col_desc, col_amt, col_by, col_split = st.columns([3, 1, 1, 2])                
                with col_desc:
                    st.write(f"**{expense['description']}**")
                    st.caption(f"{expense['category']} • {expense['date']}")                
                with col_amt:
                    st.metric("Amount", f"₹{expense['amount']}")                
                with col_by:
                    st.write(f"Paid by: **{expense['paid_by']}**")                
                with col_split:
                    st.write("Split between:")
                    st.caption(", ".join(expense['split_between']))
                
def get_ai_suggestions(expenses_data, plans_data, payments_data, user_query=""):
    try:
        context_data = {
            "trip_info": {
                "destination": "Goa",
                "dates": "October 1-5, 2024",
                "group": FRIENDS,
                "group_size": len(FRIENDS)
            },
            "expenses": expenses_data[-10:] if len(expenses_data) > 10 else expenses_data,  # Last 10 expenses
            "plans": plans_data,
            "payments": payments_data,
            "current_balances": calculate_balances()
        }
        if user_query:
            prompt = f"""
            You are a smart travel assistant for a group trip to Goa. Analyze the following trip data and answer the user's question.         
            User Question: {user_query}
            
            Trip Data: {json.dumps(context_data, indent=2)}
            
            Please provide helpful, specific suggestions based on the actual data. Be friendly and use emojis.
            """
        else:
            prompt = f"""
            You are a smart travel assistant for a group trip to Goa. Analyze the following trip data and provide helpful suggestions.
            
            Trip Data: {json.dumps(context_data, indent=2)}
            
            Based on this data, provide 3-5 specific suggestions about:
            1. Budget management and expense optimization
            2. Plan approval and activity recommendations
            3. Payment settlements
            4. General trip improvement tips
            
            Be specific, helpful, and use emojis. Keep it concise but actionable.
            """
        
        # Make API request to Google AI
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(GOOGLE_AI_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "Sorry, I couldn't generate suggestions at the moment. Please try again!"
        else:
            return f"API Error: {response.status_code}. Please check your API key or try again later."
            
    except Exception as e:
        return f"Error getting AI suggestions: {str(e)}"

def ai_management_tab():
    """AI Management tab with suggestions and chat"""
    st.subheader("🤖 AI Travel Assistant")
    st.markdown("Get intelligent suggestions based on your trip data!")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 💡 Quick Analysis")
        
        if st.button("🔍 Get AI Suggestions", type="primary"):
            with st.spinner("Analyzing your trip data..."):
                suggestions = get_ai_suggestions(
                    st.session_state.expenses, 
                    st.session_state.plans, 
                    st.session_state.payments
                )
                st.session_state.ai_suggestions = suggestions
        
        # Display suggestions
        if hasattr(st.session_state, 'ai_suggestions'):
            st.markdown("### 📋 AI Suggestions")
            st.markdown(st.session_state.ai_suggestions)
    
    with col2:
        st.markdown("### 💬 Ask AI Assistant")
        
        # Chat interface
        user_query = st.text_area(
            "Ask anything about your trip:", 
            placeholder="e.g., How can we save money? Which plans should we prioritize? Who should pay whom?",
            height=100
        )
        
        if st.button("Ask AI", type="secondary"):
            if user_query.strip():
                with st.spinner("Getting AI response..."):
                    response = get_ai_suggestions(
                        st.session_state.expenses, 
                        st.session_state.plans, 
                        st.session_state.payments,
                        user_query
                    )
                    st.session_state.ai_chat_response = response
            else:
                st.warning("Please enter a question!")
        
        # Display chat response
        if hasattr(st.session_state, 'ai_chat_response'):
            st.markdown("### 🤖 AI Response")
            st.markdown(st.session_state.ai_chat_response)
    
    st.divider()
    
    # Data overview for context
    st.markdown("### 📊 Trip Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_expenses = sum(expense['amount'] for expense in st.session_state.expenses)
        st.metric("Total Expenses", f"₹{total_expenses:,.0f}")
    
    with col2:
        pending_plans = sum(1 for plan in st.session_state.plans if plan.get('status', 'pending') != 'completed')
        st.metric("Pending Plans", pending_plans)
    
    with col3:
        total_payments = sum(payment['amount'] for payment in st.session_state.payments)
        st.metric("Payments Made", f"₹{total_payments:,.0f}")
    
    with col4:
        balances = calculate_balances()
        unsettled = sum(1 for balance in balances.values() if abs(balance) > 1)
        st.metric("Unsettled Members", unsettled)
    
    # Show recent activity
    if st.session_state.expenses or st.session_state.plans:
        st.markdown("### 📈 Recent Activity")
        
        # Combine and sort recent activities
        recent_activities = []
        
        # Add recent expenses
        for expense in st.session_state.expenses[-5:]:
            recent_activities.append({
                'type': 'expense',
                'title': f"💰 {expense['description']}",
                'details': f"₹{expense['amount']} paid by {expense['paid_by']}",
                'date': expense.get('created_at', expense.get('date'))
            })
        
        # Add recent plans
        for plan in st.session_state.plans[-3:]:
            approvals = len(plan.get('approvals', {}))
            recent_activities.append({
                'type': 'plan',
                'title': f"📋 {plan['title']}",
                'details': f"{approvals}/6 approvals • Created by {plan['created_by']}",
                'date': plan.get('created_at', plan.get('date'))
            })
        
        # Sort by date (most recent first)
        recent_activities.sort(key=lambda x: x['date'], reverse=True)
        
        for activity in recent_activities[:8]:
            st.markdown(f"**{activity['title']}**")
            st.caption(activity['details'])
            st.markdown("---")
    
    with col2:
        st.subheader("📊 Summary")
        
        total_expenses = sum(expense['amount'] for expense in st.session_state.expenses)
        st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
        
        # Category breakdown
        category_totals = {}
        for expense in st.session_state.expenses:
            category = expense['category']
            category_totals[category] = category_totals.get(category, 0) + expense['amount']
        
        if category_totals:
            fig = px.pie(
                values=list(category_totals.values()),
                names=list(category_totals.keys()),
                title="Expenses by Category"
            )
            st.plotly_chart(fig, use_container_width=True)

def show_balances():
    """Show who owes whom"""
    st.subheader("⚖️ Balances")
    
    balances = calculate_balances()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Balances:**")
        for friend, balance in balances.items():
            if balance > 0:
                st.success(f"{friend}: +₹{balance:.2f} (to receive)")
            elif balance < 0:
                st.error(f"{friend}: -₹{abs(balance):.2f} (to pay)")
            else:
                st.info(f"{friend}: ₹0.00 (settled)")
    
    with col2:
        st.subheader("💸 Record Payment")
        with st.form("payment_form"):
            from_person = st.selectbox("From", FRIENDS)
            to_person = st.selectbox("To", FRIENDS)
            payment_amount = st.number_input("Amount", min_value=0.0, step=1.0)
            
            if st.form_submit_button("Record Payment"):
                if from_person != to_person and payment_amount > 0:
                    new_payment = {
                        'id': len(st.session_state.payments) + 1,
                        'from': from_person,
                        'to': to_person,
                        'amount': payment_amount,
                        'date': datetime.now().isoformat()
                    }
                    
                    st.session_state.payments.append(new_payment)
                    save_data(st.session_state.payments, PAYMENTS_FILE)
                    st.success(f"✅ Recorded: {from_person} paid ₹{payment_amount} to {to_person}")
                    st.rerun()

def add_plan():
    """Add new plan"""
    with st.form("add_plan_form"):
        st.subheader("📋 Create New Plan")
        
        col1, col2 = st.columns(2)
        
        with col1:
            plan_title = st.text_input("Plan Title", placeholder="e.g., Beach visit at Baga")
            plan_description = st.text_area("Description", placeholder="Details about the plan...")
            plan_date = st.date_input("Planned Date")
            plan_time = st.time_input("Planned Time")
        
        with col2:
            estimated_cost = st.number_input("Estimated Cost per person (₹)", min_value=0.0, step=10.0)
            plan_category = st.selectbox("Category", ["Sightseeing", "Food", "Adventure", "Shopping", "Nightlife", "Transport", "Other"])
            created_by = st.selectbox("Created By", FRIENDS)
        
        submitted = st.form_submit_button("Create Plan", type="primary")
        
        if submitted:
            if plan_title and plan_description:
                new_plan = {
                    'id': len(st.session_state.plans) + 1,
                    'title': plan_title,
                    'description': plan_description,
                    'date': plan_date.isoformat(),
                    'time': plan_time.strftime("%H:%M"),
                    'estimated_cost': estimated_cost,
                    'category': plan_category,
                    'created_by': created_by,
                    'created_at': datetime.now().isoformat(),
                    'approvals': {},
                    'status': 'pending'
                }
                
                st.session_state.plans.append(new_plan)
                save_data(st.session_state.plans, PLANS_FILE)
                st.success(f"✅ Created plan: {plan_title}")
                st.rerun()
            else:
                st.error("Please fill in title and description")

def show_plans():
    """Display plans and voting"""
    if not st.session_state.plans:
        st.info("No plans created yet. Create your first plan above!")
        return
    
    st.subheader("🗳️ Plan Voting")
    
    for i, plan in enumerate(st.session_state.plans):
        if plan['status'] != 'completed':
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 2])
                
                with col1:
                    st.write(f"**{plan['title']}**")
                    st.write(plan['description'])
                    st.caption(f"📅 {plan['date']} at {plan['time']} • By: {plan['created_by']}")
                    if plan['estimated_cost'] > 0:
                        st.caption(f"💰 Est. cost: ₹{plan['estimated_cost']}/person")
                
                with col2:
                    # Count approvals
                    approvals = plan.get('approvals', {})
                    approved_count = sum(1 for vote in approvals.values() if vote == 'approve')
                    declined_count = sum(1 for vote in approvals.values() if vote == 'decline')
                    
                    st.metric("Approved", f"{approved_count}/6")
                    st.metric("Declined", declined_count)
                
                with col3:
                    st.write("**Vote:**")
                    
                    # Voting buttons
                    col_approve, col_decline = st.columns(2)
                    
                    with col_approve:
                        if st.button("👍 Approve", key=f"approve_{plan['id']}"):
                            if 'approvals' not in st.session_state.plans[i]:
                                st.session_state.plans[i]['approvals'] = {}
                            st.session_state.plans[i]['approvals'][st.session_state.get('voter', 'anonymous')] = 'approve'
                            save_data(st.session_state.plans, PLANS_FILE)
                            st.rerun()
                    
                    with col_decline:
                        if st.button("👎 Decline", key=f"decline_{plan['id']}"):
                            if 'approvals' not in st.session_state.plans[i]:
                                st.session_state.plans[i]['approvals'] = {}
                            st.session_state.plans[i]['approvals'][st.session_state.get('voter', 'anonymous')] = 'decline'
                            save_data(st.session_state.plans, PLANS_FILE)
                            st.rerun()
                    
                    # Show current votes
                    approvals = plan.get('approvals', {})
                    if approvals:
                        st.write("**Votes:**")
                        for voter, vote in approvals.items():
                            emoji = "✅" if vote == 'approve' else "❌"
                            st.caption(f"{emoji} {voter}")
                
                # Mark as completed if all approved
                if approved_count >= 4:  # Majority approval
                    if st.button("✨ Mark as Completed", key=f"complete_{plan['id']}"):
                        st.session_state.plans[i]['status'] = 'completed'
                        save_data(st.session_state.plans, PLANS_FILE)
                        st.rerun()
                
                st.divider()

def main():
    initialize_session_state()
    st.title("🏖️ Goa Squad Trip")
    st.markdown("**Oct 1-5, 2024 • kattu, lord, iyer, fluffy, chiknu, saky**")
    with st.sidebar:
        st.header("👤 Who are you?")
        current_user = st.selectbox("Select your name", FRIENDS)
        st.session_state.voter = current_user     
        st.divider()
        total_expenses = sum(expense['amount'] for expense in st.session_state.expenses)
        pending_plans = sum(1 for plan in st.session_state.plans if plan['status'] != 'completed')      
        st.metric("Total Expenses", f"₹{total_expenses:,.0f}")
        st.metric("Active Plans", pending_plans)
    tab1, tab2, tab3 = st.tabs(["💰 Expenses", "📋 Plans", "🤖 AI Assistant"])    
    with tab1:
        add_expense()
        st.divider()
        show_expenses()
        st.divider()
        show_balances()    
    with tab2:
        add_plan()
        st.divider()
        show_plans()    
    with tab3:
        ai_management_tab()

if __name__ == "__main__":
    main()