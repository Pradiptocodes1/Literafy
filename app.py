from flask import Flask, request, send_file, render_template_string, session
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.units import inch
from reportlab.lib.fonts import addMapping
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import requests
import json
from datetime import datetime
import time

app = Flask(__name__)

MISTRAL_API_KEY = "SKYjG5bL2rn3nnMwhNtXazBs0MFNteih"
SERPAPI_API_KEY = "c3648cf164f14a2278308e6816b7daea1fd6dac01fe264d9be8edc01b9197c2d"

mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# Use built-in fonts instead of Times New Roman
addMapping('Times-Roman', 0, 0, 'Times-Roman')
addMapping('Times-Roman', 1, 0, 'Times-Bold')

def call_mistral_api(prompt):
    messages = [
        ChatMessage(role="user", content=prompt)
    ]
    chat_response = mistral_client.chat(
        model="mistral-small",
        messages=messages,
    )
    return chat_response.choices[0].message.content

def search_google_scholar(query):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": 20
    }
    response = requests.get(url, params=params)
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except json.JSONDecodeError:
        print("Failed to decode JSON. Response content:")
        print(response.content)
        return {}

def generate_citation(paper):
    title = paper.get('title', 'Unknown Title')
    summary = paper.get('publication_info', {}).get('summary', '')
    
    prompt = f"""Create a proper citation for the following paper:
Title: {title}
Summary: {summary}

Format the citation in the style similar to this example:
Ching, Travers, et al. "Opportunities and obstacles for deep learning in biology and medicine." Journal of the royal society interface 15.141 (2018): 20170387.

Provide only the formatted citation, without any additional text."""

    citation = call_mistral_api(prompt)
    return citation.strip()

def generate_literature_review(papers):
    review = ""
    citations = []
    links = []
    for i, paper in enumerate(papers, 1):
        title = paper.get('title', 'Unknown Title')
        abstract = paper.get('snippet', 'No abstract available')
        link = paper.get('link', '')
        
        prompt = f"""Summarize the following research paper:
Title: {title}
Abstract: {abstract}

Provide a comprehensive summary that includes the following elements, dont include anything which is not in the abstract. Basically everything should be from abstrsct only:
1. Introduce the paper with its title.
2. Briefly describe the main focus or problem addressed in the research.
3. Outline the key methods or approaches used.
4. Summarize the main findings or conclusions.
5. If applicable, mention any significant implications or applications of the research.

In the end justify if this research aligns with the research title, give a score out of 10.

Your summary should be a cohesive paragraph that flows naturally and avoids simply restating the abstract. 
Include the citation number [{i}] at appropriate places within the text, not just at the end."""

        summary = call_mistral_api(prompt)
        review += f"{i}. {summary}\n\n\n"
        
        citation = generate_citation(paper)
        citations.append((i, citation))
        links.append((i, link))
    
    return review, citations, links

def create_pdf(content, citations, links, query):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch,
                            title="Literature Review")
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justified',
                              fontName='Times-Roman',
                              fontSize=12,
                              alignment=4,  
                              spaceAfter=0))  
    
 
    styles['Title'].fontName = 'Times-Bold'
    styles['Title'].fontSize = 16
    styles['Title'].alignment = 1  
    
    
    styles['Heading1'].fontName = 'Times-Bold'
    styles['Heading1'].fontSize = 14
    styles['Heading1'].alignment = 0  
    
    story = []
    
    
    story.append(Paragraph(f"Literature Review: {query}", styles['Title']))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Justified']))
    story.append(Paragraph(f"---Literafy by CiteWise", styles['Justified']))
    story.append(PageBreak())
    
    for paragraph in content.split('\n\n'):
        story.append(Paragraph(paragraph, styles['Justified']))
    
    story.append(PageBreak())
    story.append(Paragraph("Bibliography", styles['Heading1']))
    story.append(Spacer(1, 12))  
    for number, citation in citations:
        story.append(Paragraph(f"[{number}] {citation}", styles['Justified']))
        story.append(Spacer(1, 6))  
    

    story.append(Paragraph("Links", styles['Heading1']))
    story.append(Spacer(1, 12))  
    for number, link in links:
        story.append(Paragraph(f"[{number}] {link}", styles['Justified']))
        story.append(Spacer(1, 6))  
    
   
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        search_results = search_google_scholar(query)
        papers = search_results.get('organic_results', [])
        
        literature_review, citations, links = generate_literature_review(papers)
        
        pdf_buffer = create_pdf(literature_review, citations, links, query)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f'literature_review_{query.replace(" ", "_")}.pdf',
            mimetype='application/pdf'
        )

    
    time_taken = session.get('time_taken')
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Literature Review Generator</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playwrite+BE+VLG:wght@100..400&display=swap" rel="stylesheet">
    <style>
        @import url("https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap");

        :root {
            --body-color: #FEF3E2;
            --input-color: #BEC6A0;
            --button-color: #708871;
            --accent-color: #4CAF50;
            --white-color: #fff;
            --box-shadow: 0 0 5px #4CAF50, 0 0 25px #4CAF50, 0 0 50px #4CAF50,
                0 0 100px #4CAF50;
        }

        * {
            box-sizing: border-box;
            padding: 0;
            margin: 0;
        }

        body {
            font-family: "Montserrat", sans-serif;
            font-size: 1rem;
            background: var(--body-color);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .playwrite-be-vlg-heading {
            font-family: "Playwrite BE VLG", cursive;
            font-optical-sizing: auto;
            font-weight: 1000;
            font-style: normal;
        }

        h1 {
            margin-bottom: 2rem;
            color: #333;
        }

        form {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        label {
            margin-bottom: 0.5rem;
            color: #333;
        }

        input[type="text"] {
            width: 300px;
            padding: 10px;
            margin-bottom: 1rem;
            background-color: var(--input-color);
            border: none;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }

        input[type="text"]:focus {
            outline: none;
            box-shadow: none;
            animation: glow 1.5s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from {
                box-shadow: 0 0 5px #8BC34A, 0 0 10px #8BC34A;
            }
            to {
                box-shadow: 0 0 10px #4CAF50, 0 0 20px #4CAF50;
            }
        }

        button[type="submit"] {
            padding: 10px 20px;
            background-color: var(--button-color);
            color: var(--white-color);
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        button[type="submit"]:hover {
            background-color: var(--accent-color);
            box-shadow: var(--box-shadow);
        }

        button[type="submit"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                120deg,
                transparent,
                rgba(255, 255, 255, 0.4),
                transparent
            );
            transition: all 0.5s;
        }

        button[type="submit"]:hover::before {
            left: 100%;
        }

        .loader {
            display: inline-grid;
            width: 90px;
            aspect-ratio: 1;
            clip-path: polygon(100% 50%,85.36% 85.36%,50% 100%,14.64% 85.36%,0% 50%,14.64% 14.64%,50% 0%,85.36% 14.64%);
            background: #574951;
            animation: l2 6s infinite linear;
        }
        .loader:before,
        .loader:after {
            content:"";
            grid-area: 1/1;
            background: #83988E;
            clip-path: polygon(100% 50%,81.17% 89.09%,38.87% 98.75%,4.95% 71.69%,4.95% 28.31%,38.87% 1.25%,81.17% 10.91%);
            margin: 10%;
            animation: inherit;
            animation-duration: 10s;
        }
        .loader:after {
            background: #BCDEA5;
            clip-path: polygon(100% 50%,75% 93.3%,25% 93.3%,0% 50%,25% 6.7%,75% 6.7%);
            margin: 20%;
            animation-duration: 3s;
            animation-direction: reverse;
        }
        @keyframes l2 {to{rotate: 1turn}}

        #successMessage {
            display: none;
            color: var(--accent-color);
            font-weight: bold;
            margin-top: 1rem;
        }
        .button-container {
            display: flex;
            gap: 10px;
        }

        .back-button {
            padding: 10px 20px;
            background-color: var(--input-color);
            color: #333;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: all 0.3s ease;
            font-size: 0.8em;
        }

        .back-button:hover {
            background-color: #A0A78B;
            color: var(--white-color);
        }
    </style>
</head>
<body>
    <h1 class="playwrite-be-vlg-heading">Literafy.</h1>
    <form method="post" id="reviewForm">
        <label for="query">Enter your research topic:</label>
        <input type="text" id="query" name="query" required><br><br>
        <button type="submit" id="submitButton" style="font-size: 0.8em; text-transform: none;">Generate literature review</button><br>
        <a href="https://www.citewise.tech/toolkitspage.html"><button type="button" id="backButton" class="back-button">Back</button></a>
        <div class="loader" style="display: none;"></div>
        <div id="successMessage">Generated successfully</div>
    </form>

    <script>
    document.getElementById('reviewForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const form = this;
        const submitButton = document.getElementById('submitButton');
        const loader = document.querySelector('.loader');
        const successMessage = document.getElementById('successMessage');

        submitButton.style.display = 'none';
        loader.style.display = 'inline-grid';
        successMessage.style.display = 'none';

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.blob();
        })
        .then(blob => {
            // Create a temporary URL for the blob
            const url = window.URL.createObjectURL(blob);
            
            // Create a temporary anchor element and trigger the download
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'literature_review.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            
            // Show success message and hide loader
            loader.style.display = 'none';
            successMessage.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            loader.style.display = 'none';
            submitButton.style.display = 'block';
            alert('An error occurred. Please try again.');
        });
    });
    </script>
</body>
</html>
    ''')

if __name__ == '__main__':
    app.run(debug=True)
