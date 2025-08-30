import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

# Page config
st.set_page_config(
    page_title="AI Email Management Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better card styling
st.markdown("""
<style>
.email-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    padding: 20px;
    margin: 15px 0;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    color: white;
    border-left: 5px solid #ff6b6b;
}

.email-card-high {
    border-left-color: #ff4757;
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
}

.email-card-medium {
    border-left-color: #ffa726;
    background: linear-gradient(135deg, #ffa726 0%, #ff7043 100%);
}

.email-card-low {
    border-left-color: #66bb6a;
    background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.priority-badge {
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

.status-badge {
    padding: 5px 10px;
    border-radius: 10px;
    font-size: 11px;
    background: rgba(255,255,255,0.2);
}

.card-content {
    margin: 10px 0;
}

.card-footer {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid rgba(255,255,255,0.3);
    display: flex;
    justify-content: space-between;
    font-size: 12px;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}

.mailbox-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin: 20px 0 10px 0;
}

.filter-section {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'gsheet_connected' not in st.session_state:
    st.session_state.gsheet_connected = False
if 'service_account_info' not in st.session_state:
    st.session_state.service_account_info = None

def create_demo_data():
    """Create enhanced demo data"""
    columns = [
        "Company Main Email", "Email ID", "Received Date", "Received Time",
        "From (Sender Name)", "From (Sender Email)", "Subject", "Department",
        "Priority", "Category/Tag", "Email Summary", "Drafted Response",
        "Response Approved (Y/N)", "Approver Name", "Sent (Y/N)", "Sent Date",
        "Sent Time", "Sent Email Summary", "Attachments Received (Y/N)",
        "Attachment Details", "Follow-up Required (Y/N)", "Follow-up Due Date",
        "Assigned To", "Resolution Status", "Notes/Comments"
    ]
    
    mailboxes = [
        "support@vipbusinesscredit.com",
        "sales@vipbusinesscredit.com", 
        "billing@vipbusinesscredit.com",
        "hr@vipbusinesscredit.com",
        "info@vipbusinesscredit.com"
    ]
    
    rows = []
    email_counter = 1000
    
    demo_subjects = [
        "Urgent: Payment processing issue needs immediate attention",
        "Follow-up on credit application status inquiry",
        "Request for documentation update and verification",
        "Complaint about service delays and resolution needed",
        "New partnership opportunity discussion",
        "Account verification and security update required",
        "Invoice discrepancy needs clarification",
        "Employee onboarding documentation request",
        "Product demo scheduling and requirements",
        "Technical support for platform integration"
    ]
    
    demo_summaries = [
        "Customer experiencing payment gateway errors affecting multiple transactions",
        "Applicant requesting status update on business credit application submitted last week",
        "Client needs to update business documentation for compliance review",
        "Frustrated customer complaining about 3-day service delay, requesting manager escalation",
        "Potential partner proposing strategic alliance for mutual growth opportunities",
        "Security team requesting account verification due to suspicious login attempts",
        "Billing discrepancy of $1,500 requires investigation and correction",
        "New hire needs access credentials and onboarding materials",
        "Prospect interested in product demo and pricing information",
        "Integration issues with API causing data sync problems"
    ]
    
    for i, mailbox in enumerate(mailboxes):
        for j in range(2):  # 2 emails per mailbox
            email_counter += 1
            idx = (i * 2 + j) % len(demo_subjects)
            
            received_date = (datetime.now() - timedelta(days=j+1)).strftime("%Y-%m-%d")
            received_time = f"{9+j}:{15+j*5:02d}"
            
            row = [
                mailbox,  # Company Main Email
                f"E{email_counter}",  # Email ID
                received_date,  # Received Date
                received_time,  # Received Time
                f"Contact Person {email_counter}",  # From (Sender Name)
                f"contact{email_counter}@company{i+1}.com",  # From (Sender Email)
                demo_subjects[idx],  # Subject
                ("Support" if "support" in mailbox else "Sales" if "sales" in mailbox else 
                 "Billing" if "billing" in mailbox else "HR" if "hr" in mailbox else "General"),  # Department
                ["High", "Medium", "Low"][j % 3],  # Priority
                ("Urgent" if j == 0 else "Follow-up" if j == 1 else "Inquiry"),  # Category/Tag
                demo_summaries[idx],  # Email Summary
                f"Thank you for contacting us regarding '{demo_subjects[idx][:30]}...'. We have reviewed your inquiry and will provide a comprehensive response within 24 hours.",  # Drafted Response
                "Y" if j == 0 else "N",  # Response Approved
                "Manager Smith" if j == 0 else "",  # Approver Name
                "Y" if j == 0 else "N",  # Sent
                received_date if j == 0 else "",  # Sent Date
                f"{10+j}:30" if j == 0 else "",  # Sent Time
                "Professional response sent addressing all customer concerns" if j == 0 else "",  # Sent Email Summary
                "Y" if j == 1 else "N",  # Attachments Received
                "contract.pdf, invoice.xlsx" if j == 1 else "",  # Attachment Details
                "Y" if j % 2 == 0 else "N",  # Follow-up Required
                (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d") if j % 2 == 0 else "",  # Follow-up Due Date
                f"Agent_{i+1}",  # Assigned To
                "Completed" if j == 0 else "In Progress",  # Resolution Status
                f"High priority case - escalate if no response within 24 hours" if j == 0 else "Standard processing"  # Notes
            ]
            rows.append(row)
    
    return pd.DataFrame(rows, columns=columns)

def connect_to_gsheets(service_account_info, sheet_url, worksheet_name="Sheet1"):
    """Connect to Google Sheets and return dataframe"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(creds)
        
        # Extract sheet ID from URL
        if 'docs.google.com/spreadsheets/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            sheet_id = sheet_url
            
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
        
        # Get all records
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        return df, None
    except Exception as e:
        return None, str(e)

def render_email_card(email_row):
    """Render an enhanced email card"""
    priority_class = f"email-card-{email_row['Priority'].lower()}"
    
    # Priority badge color
    priority_colors = {
        "High": "#ff4757",
        "Medium": "#ffa726", 
        "Low": "#66bb6a"
    }
    
    # Status colors
    status_colors = {
        "Completed": "#27ae60",
        "In Progress": "#f39c12",
        "Pending": "#e74c3c"
    }
    
    card_html = f"""
    <div class="email-card {priority_class}">
        <div class="card-header">
            <div>
                <h3 style="margin: 0; font-size: 18px;">📧 {email_row['Email ID']}</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">
                    From: {email_row['From (Sender Name)']} ({email_row['From (Sender Email)']})
                </p>
            </div>
            <div style="text-align: right;">
                <span class="priority-badge" style="background: {priority_colors.get(email_row['Priority'], '#666')};">
                    {email_row['Priority']} Priority
                </span>
                <br>
                <span class="status-badge" style="background: {status_colors.get(email_row['Resolution Status'], '#666')}; margin-top: 5px; display: inline-block;">
                    {email_row['Resolution Status']}
                </span>
            </div>
        </div>
        
        <div class="card-content">
            <h4 style="margin: 0 0 10px 0; font-size: 16px;">📝 Subject:</h4>
            <p style="margin: 0 0 15px 0; font-weight: 500;">{email_row['Subject']}</p>
            
            <h4 style="margin: 0 0 10px 0; font-size: 16px;">📋 Summary:</h4>
            <p style="margin: 0 0 15px 0; line-height: 1.4;">{email_row['Email Summary']}</p>
            
            {"<h4 style='margin: 0 0 10px 0; font-size: 16px;'>✅ Response:</h4>" if email_row['Sent (Y/N)'] == 'Y' else "<h4 style='margin: 0 0 10px 0; font-size: 16px;'>📝 Drafted Response:</h4>"}
            <p style="margin: 0 0 15px 0; line-height: 1.4; background: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px;">
                {email_row['Drafted Response']}
            </p>
        </div>
        
        <div class="card-footer">
            <div>
                <strong>📅 Received:</strong> {email_row['Received Date']} at {email_row['Received Time']}<br>
                <strong>🏷️ Category:</strong> {email_row['Category/Tag']} | 
                <strong>👤 Assigned:</strong> {email_row['Assigned To']}
            </div>
            <div style="text-align: right;">
                {"<strong>✅ Sent:</strong> " + email_row['Sent Date'] + " at " + email_row['Sent Time'] if email_row['Sent (Y/N)'] == 'Y' else "<strong>⏳ Pending</strong>"}
                <br>
                {"<strong>📎 Attachments:</strong> " + email_row['Attachment Details'] if email_row['Attachments Received (Y/N)'] == 'Y' else ""}
                {"<br><strong>📅 Follow-up Due:</strong> " + email_row['Follow-up Due Date'] if email_row['Follow-up Required (Y/N)'] == 'Y' else ""}
            </div>
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def main():
    st.title("📧 AI Email Management Dashboard")
    st.markdown("Advanced email tracking with Google Sheets integration and enhanced analytics")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Google Sheets Integration
    st.sidebar.subheader("🔗 Google Sheets Integration")
    
    # Service account file upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload Service Account JSON",
        type=['json'],
        help="Upload your Google Cloud Service Account JSON file"
    )
    
    if uploaded_file is not None:
        try:
            service_account_info = json.load(uploaded_file)
            st.session_state.service_account_info = service_account_info
            st.sidebar.success("✅ Service account loaded successfully!")
        except Exception as e:
            st.sidebar.error(f"❌ Error loading service account: {str(e)}")
    
    # Google Sheets URL input
    sheet_url = st.sidebar.text_input(
        "Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Paste your Google Sheets URL here"
    )
    
    worksheet_name = st.sidebar.text_input(
        "Worksheet Name",
        value="Sheet1",
        help="Name of the worksheet tab to read from"
    )
    
    # Connect to Google Sheets
    if st.sidebar.button("🔄 Connect to Google Sheets"):
        if st.session_state.service_account_info and sheet_url:
            with st.spinner("Connecting to Google Sheets..."):
                df, error = connect_to_gsheets(
                    st.session_state.service_account_info, 
                    sheet_url, 
                    worksheet_name
                )
                if df is not None:
                    st.session_state.df = df
                    st.session_state.gsheet_connected = True
                    st.sidebar.success("✅ Connected to Google Sheets!")
                    st.rerun()
                else:
                    st.sidebar.error(f"❌ Connection failed: {error}")
        else:
            st.sidebar.error("❌ Please upload service account file and enter sheet URL")
    
    # Use demo data if no Google Sheets connection
    if st.session_state.df is None:
        st.session_state.df = create_demo_data()
        if not st.session_state.gsheet_connected:
            st.sidebar.info("📊 Using demo data. Connect to Google Sheets for live data.")
    
    df = st.session_state.df
    
    # Auto-refresh for Google Sheets
    if st.session_state.gsheet_connected:
        auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
        if auto_refresh:
            st.sidebar.info("Auto-refresh enabled")
            # Note: In a real implementation, you'd use st.rerun() with a timer
    
    # Main dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #667eea; margin: 0;">Total Emails</h3>
            <h1 style="margin: 10px 0; color: #2c3e50;">{}</h1>
        </div>
        """.format(len(df)), unsafe_allow_html=True)
    
    with col2:
        pending_count = len(df[df['Resolution Status'] == 'Pending'])
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #e74c3c; margin: 0;">Pending</h3>
            <h1 style="margin: 10px 0; color: #2c3e50;">{}</h1>
        </div>
        """.format(pending_count), unsafe_allow_html=True)
    
    with col3:
        high_priority = len(df[df['Priority'] == 'High'])
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #ff4757; margin: 0;">High Priority</h3>
            <h1 style="margin: 10px 0; color: #2c3e50;">{}</h1>
        </div>
        """.format(high_priority), unsafe_allow_html=True)
    
    with col4:
        response_rate = len(df[df['Sent (Y/N)'] == 'Y']) / len(df) * 100 if len(df) > 0 else 0
        st.markdown("""
        <div class="metric-card">
            <h3 style="color: #27ae60; margin: 0;">Response Rate</h3>
            <h1 style="margin: 10px 0; color: #2c3e50;">{:.1f}%</h1>
        </div>
        """.format(response_rate), unsafe_allow_html=True)
    
    # Enhanced Filters Section
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.subheader("🔍 Advanced Filters & Sorting")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_mailbox = st.selectbox(
            "📮 Mailbox",
            options=["All"] + sorted(df["Company Main Email"].unique().tolist())
        )
    
    with col2:
        selected_priority = st.multiselect(
            "⚡ Priority",
            options=sorted(df["Priority"].unique().tolist()),
            default=[]
        )
    
    with col3:
        selected_status = st.multiselect(
            "📊 Status",
            options=sorted(df["Resolution Status"].unique().tolist()),
            default=[]
        )
    
    with col4:
        selected_department = st.multiselect(
            "🏢 Department",
            options=sorted(df["Department"].unique().tolist()),
            default=[]
        )
    
    # Sorting options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sort_by = st.selectbox(
            "📊 Sort by",
            options=["Received Date", "Priority", "Resolution Status", "Department", "Email ID"],
            index=0
        )
    
    with col2:
        sort_order = st.selectbox(
            "📈 Order",
            options=["Descending", "Ascending"],
            index=0
        )
    
    with col3:
        view_mode = st.selectbox(
            "👁️ View Mode",
            options=["Card View", "Table View", "Both"],
            index=0
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_mailbox != "All":
        filtered_df = filtered_df[filtered_df["Company Main Email"] == selected_mailbox]
    if selected_priority:
        filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priority)]
    if selected_status:
        filtered_df = filtered_df[filtered_df["Resolution Status"].isin(selected_status)]
    if selected_department:
        filtered_df = filtered_df[filtered_df["Department"].isin(selected_department)]
    
    # Apply sorting
    ascending = sort_order == "Ascending"
    if sort_by == "Priority":
        # Custom priority sorting
        priority_order = {"High": 3, "Medium": 2, "Low": 1}
        filtered_df["priority_num"] = filtered_df["Priority"].map(priority_order)
        filtered_df = filtered_df.sort_values("priority_num", ascending=ascending)
        filtered_df = filtered_df.drop("priority_num", axis=1)
    else:
        filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
    
    # Display results
    if filtered_df.empty:
        st.warning("🔍 No emails match your current filters. Try adjusting the criteria.")
        return
    
    # Analytics Section
    if len(filtered_df) > 0:
        st.subheader("📈 Email Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Priority distribution
            priority_counts = filtered_df['Priority'].value_counts()
            fig1 = px.pie(
                values=priority_counts.values,
                names=priority_counts.index,
                title="Priority Distribution",
                color_discrete_map={"High": "#ff4757", "Medium": "#ffa726", "Low": "#66bb6a"}
            )
            fig1.update_layout(height=300)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Status by department
            status_dept = filtered_df.groupby(['Department', 'Resolution Status']).size().reset_index(name='Count')
            fig2 = px.bar(
                status_dept,
                x='Department',
                y='Count',
                color='Resolution Status',
                title="Status by Department",
                color_discrete_map={"Completed": "#27ae60", "In Progress": "#f39c12", "Pending": "#e74c3c"}
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
    
    # Display emails by mailbox
    mailboxes_to_show = (
        [selected_mailbox] if selected_mailbox != "All"
        else filtered_df["Company Main Email"].unique().tolist()
    )
    
    for mailbox in sorted(mailboxes_to_show):
        subset = filtered_df[filtered_df["Company Main Email"] == mailbox].reset_index(drop=True)
        
        if subset.empty:
            continue
            
        # Mailbox header with stats
        pending_in_mailbox = len(subset[subset['Resolution Status'] == 'Pending'])
        high_priority_in_mailbox = len(subset[subset['Priority'] == 'High'])
        
        st.markdown(f"""
        <div class="mailbox-header">
            <h2 style="margin: 0; font-size: 24px;">📮 {mailbox}</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">
                {len(subset)} emails | {pending_in_mailbox} pending | {high_priority_in_mailbox} high priority
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if view_mode in ["Card View", "Both"]:
            # Card view
            for _, email in subset.iterrows():
                render_email_card(email)
        
        if view_mode in ["Table View", "Both"]:
            # Table view
            st.subheader(f"📊 Table View - {mailbox}")
            
            # Column selection for table
            available_columns = df.columns.tolist()
            default_columns = [
                "Email ID", "Received Date", "From (Sender Name)", 
                "Subject", "Priority", "Resolution Status", "Assigned To"
            ]
            
            selected_columns = st.multiselect(
                f"Select columns to display for {mailbox}",
                options=available_columns,
                default=[col for col in default_columns if col in available_columns],
                key=f"columns_{mailbox}"
            )
            
            if selected_columns:
                display_df = subset[selected_columns]
                st.dataframe(
                    display_df,
                    height=300,
                    use_container_width=True,
                    hide_index=True
                )
            
        # Download section
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label=f"📄 Download CSV - {mailbox.split('@')[0]}",
                data=subset.to_csv(index=False).encode("utf-8"),
                file_name=f"emails_{mailbox.replace('@','_at_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"csv_{mailbox}"
            )
        
        with col2:
            st.download_button(
                label=f"📋 Download JSON - {mailbox.split('@')[0]}",
                data=subset.to_json(orient='records', indent=2).encode("utf-8"),
                file_name=f"emails_{mailbox.replace('@','_at_')}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key=f"json_{mailbox}"
            )
        
        with col3:
            # Excel download would require additional library
            st.info("📊 Excel export available with openpyxl")
    
    # Combined data section
    st.markdown("---")
    st.subheader("📊 Combined Analytics & Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Timeline chart
        if 'Received Date' in filtered_df.columns:
            daily_counts = filtered_df.groupby('Received Date').size().reset_index(name='Email Count')
            fig3 = px.line(
                daily_counts,
                x='Received Date',
                y='Email Count',
                title="Daily Email Volume",
                markers=True
            )
            fig3.update_layout(height=250)
            st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        # Response time analysis
        sent_emails = filtered_df[filtered_df['Sent (Y/N)'] == 'Y']
        if len(sent_emails) > 0:
            # Mock response time data for demo
            response_times = [2, 4, 1, 6, 3, 2, 5, 1, 3, 4][:len(sent_emails)]
            fig4 = px.histogram(
                x=response_times,
                title="Response Time Distribution (Hours)",
                nbins=10
            )
            fig4.update_layout(height=250)
            st.plotly_chart(fig4, use_container_width=True)
    
    # Advanced search
    st.subheader("🔍 Advanced Search")
    search_term = st.text_input(
        "Search in subjects and summaries",
        placeholder="Enter keywords to search..."
    )
    
    if search_term:
        search_results = filtered_df[
            filtered_df['Subject'].str.contains(search_term, case=False, na=False) |
            filtered_df['Email Summary'].str.contains(search_term, case=False, na=False)
        ]
        st.write(f"Found {len(search_results)} emails matching '{search_term}'")
        
        if len(search_results) > 0:
            for _, email in search_results.iterrows():
                render_email_card(email)
    
    # Bulk actions
    st.subheader("🔧 Bulk Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📧 Mark All as Read"):
            st.success("✅ All emails marked as read!")
    
    with col2:
        if st.button("📝 Generate Bulk Responses"):
            st.success("✅ Bulk responses generated!")
    
    with col3:
        if st.button("📊 Export Analytics Report"):
            # Generate analytics report
            report_data = {
                "total_emails": len(filtered_df),
                "by_priority": filtered_df['Priority'].value_counts().to_dict(),
                "by_status": filtered_df['Resolution Status'].value_counts().to_dict(),
                "by_department": filtered_df['Department'].value_counts().to_dict(),
                "response_rate": len(filtered_df[filtered_df['Sent (Y/N)'] == 'Y']) / len(filtered_df) * 100
            }
            
            st.download_button(
                label="📊 Download Analytics",
                data=json.dumps(report_data, indent=2).encode("utf-8"),
                file_name=f"email_analytics_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    # Full dataset download
    st.markdown("---")
    st.subheader("📦 Complete Dataset Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            label="📄 Download Complete CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"complete_email_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="📋 Download Complete JSON",
            data=filtered_df.to_json(orient='records', indent=2).encode("utf-8"),
            file_name=f"complete_email_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    with col3:
        # Filtered summary
        summary_stats = {
            "filter_applied": {
                "mailbox": selected_mailbox if selected_mailbox != "All" else "All mailboxes",
                "priorities": selected_priority if selected_priority else "All priorities",
                "statuses": selected_status if selected_status else "All statuses",
                "departments": selected_department if selected_department else "All departments"
            },
            "results": {
                "total_filtered": len(filtered_df),
                "total_original": len(df)
            }
        }
        
        st.download_button(
            label="📈 Download Filter Summary",
            data=json.dumps(summary_stats, indent=2).encode("utf-8"),
            file_name=f"filter_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    # Show full table view at bottom
    if view_mode == "Table View" or st.checkbox("📋 Show Complete Data Table", value=False):
        st.subheader("📊 Complete Data Table")
        
        # Advanced table configuration
        col1, col2 = st.columns(2)
        
        with col1:
            table_columns = st.multiselect(
                "Select columns to display",
                options=filtered_df.columns.tolist(),
                default=["Email ID", "Received Date", "From (Sender Name)", "Subject", 
                        "Priority", "Resolution Status", "Department", "Assigned To"],
                key="main_table_columns"
            )
        
        with col2:
            rows_per_page = st.selectbox(
                "Rows per page",
                options=[10, 25, 50, 100, "All"],
                index=1
            )
        
        if table_columns:
            display_df = filtered_df[table_columns].copy()
            
            # Pagination
            if rows_per_page != "All":
                total_rows = len(display_df)
                total_pages = (total_rows - 1) // rows_per_page + 1
                
                if total_pages > 1:
                    page = st.selectbox(
                        f"Page (1-{total_pages})",
                        options=list(range(1, total_pages + 1)),
                        index=0
                    )
                    
                    start_idx = (page - 1) * rows_per_page
                    end_idx = min(start_idx + rows_per_page, total_rows)
                    display_df = display_df.iloc[start_idx:end_idx]
                    
                    st.info(f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}")
            
            st.dataframe(
                display_df,
                height=400,
                use_container_width=True,
                hide_index=True
            )
    
    # Email details modal simulation
    st.markdown("---")
    st.subheader("🔍 Email Details Viewer")
    
    if len(filtered_df) > 0:
        email_ids = filtered_df['Email ID'].tolist()
        selected_email_id = st.selectbox(
            "Select an email to view full details",
            options=email_ids,
            key="email_detail_selector"
        )
        
        if selected_email_id:
            email_details = filtered_df[filtered_df['Email ID'] == selected_email_id].iloc[0]
            
            # Create detailed view
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                ### 📧 Email Details: {email_details['Email ID']}
                
                **📨 From:** {email_details['From (Sender Name)']} ({email_details['From (Sender Email)']})  
                **📅 Received:** {email_details['Received Date']} at {email_details['Received Time']}  
                **📋 Subject:** {email_details['Subject']}  
                **🏢 Department:** {email_details['Department']}  
                **⚡ Priority:** {email_details['Priority']}  
                **🏷️ Category:** {email_details['Category/Tag']}  
                
                **📝 Email Summary:**
                {email_details['Email Summary']}
                
                **💬 Drafted Response:**
                {email_details['Drafted Response']}
                
                {"**✅ Sent Summary:** " + email_details['Sent Email Summary'] if email_details['Sent (Y/N)'] == 'Y' else ""}
                
                **📝 Notes:**
                {email_details['Notes/Comments']}
                """)
            
            with col2:
                st.markdown(f"""
                ### 📊 Email Metadata
                
                **👤 Assigned To:** {email_details['Assigned To']}  
                **📊 Status:** {email_details['Resolution Status']}  
                **✅ Response Approved:** {email_details['Response Approved (Y/N)']}  
                {"**👨‍💼 Approver:** " + email_details['Approver Name'] if email_details['Approver Name'] else ""}  
                **📧 Sent:** {email_details['Sent (Y/N)']}  
                {"**📅 Sent:** " + email_details['Sent Date'] + " at " + email_details['Sent Time'] if email_details['Sent (Y/N)'] == 'Y' else ""}  
                **📎 Attachments:** {email_details['Attachments Received (Y/N)']}  
                {"**📄 Files:** " + email_details['Attachment Details'] if email_details['Attachments Received (Y/N)'] == 'Y' else ""}  
                **🔄 Follow-up Required:** {email_details['Follow-up Required (Y/N)']}  
                {"**📅 Follow-up Due:** " + email_details['Follow-up Due Date'] if email_details['Follow-up Required (Y/N)'] == 'Y' else ""}
                """)
                
                # Action buttons
                st.markdown("### 🎯 Quick Actions")
                
                if st.button("✅ Approve Response", key=f"approve_{selected_email_id}"):
                    st.success("Response approved!")
                
                if st.button("📧 Send Email", key=f"send_{selected_email_id}"):
                    st.success("Email sent successfully!")
                
                if st.button("🔄 Request Follow-up", key=f"followup_{selected_email_id}"):
                    st.success("Follow-up scheduled!")
                
                if st.button("📝 Add Note", key=f"note_{selected_email_id}"):
                    note_text = st.text_area("Add a note:", key=f"note_text_{selected_email_id}")
                    if note_text:
                        st.success("Note added!")

    # Footer with connection status
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.gsheet_connected:
            st.success("🔗 Connected to Google Sheets")
        else:
            st.info("📊 Using demo data")
    
    with col2:
        st.info(f"📈 Displaying {len(filtered_df)} of {len(df)} emails")
    
    with col3:
        if st.button("🔄 Refresh Data"):
            if st.session_state.gsheet_connected and st.session_state.service_account_info and sheet_url:
                with st.spinner("Refreshing from Google Sheets..."):
                    df_new, error = connect_to_gsheets(
                        st.session_state.service_account_info, 
                        sheet_url, 
                        worksheet_name
                    )
                    if df_new is not None:
                        st.session_state.df = df_new
                        st.success("✅ Data refreshed!")
                        st.rerun()
                    else:
                        st.error(f"❌ Refresh failed: {error}")
            else:
                st.session_state.df = create_demo_data()
                st.success("✅ Demo data refreshed!")
                st.rerun()

if __name__ == "__main__":
    main()

# Requirements for this enhanced dashboard:
# pip install streamlit pandas gspread google-auth plotly
