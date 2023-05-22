import requests
from pprint import pp  
import json
from notion_client import Client
import openai
import time
import os
import re

# This allows to retry when OpenAI isn't working
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

# necessary secrets
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
NOTION_API_KEY = os.environ['NOTION_API_KEY'] 
X_RAPID_API_KEY = os.environ['X_RAPID_API_KEY'] 
NOTION_DB_ID = os.environ['NOTION_DB_ID']
pre_prompt = """
Tu es un commercial expérimenté dans la Tech / IT et tu collectes des informations stratégiques de prospects en te basant sur des informations issues du réseau linkedin.
Voici un texte au format JSON qui représente un prospect utilisateur linkedin et ses activités sur le réseau social professionnel linkedin : 
'bio' : la description de l'utilisateur
'posts rédigés par l\'utilisateur\' : la liste de posts rédigés par l\'utilisateur
'posts commentés par l\'utilisateur\' : la liste de posts commentés par l\'utilisateur (attention, ce ne sont pas des posts écrit par l\'utilisateur)
'post ayant fait réagir l\'utilisateur\' : la liste de posts sur lesquel l\'utilisateur a réagi (réagi veut dire \'liké\' mais ne veut pas dire rédigé par l\'utilisateur)
La bio de l\'utilisateur peut contenir des informations importantes, je veux que tu notes les points notables de la bio si la bio n\'est pas vide.
En fonction des éléments de ce texte au format JSON, tu me listeras quelques thèmes qui intéressent l\'utilisateur dans la sphère professionnelle classés par ordre d\'importance pour l\'utilisateur.
Tu indiqueras un thème par ligne comme une liste de bullet points.
Puis tu résumeras en 3 lignes le post rédigé par l\'utilisateur qui est le plus pertinent et aussi le plus récent.
Tu m\'indiqueras la fraicheur de ce post à la suite du résumé du post dans ton output.
Tu m\'indiqueras sur une nouvelle ligne les quelques mots clefs importants relatifs à la technologie que tu as détectés pour cet utilisateur.
Tu indiqueras un mot clef par ligne comme une liste de bullet points.
Enfin, dis-moi si tu penses que l\'utilisateur est actif sur le réseau linkedin.
Si il ne l\'est pas alors tu indiqueras \"UTILISATEUR NON ACTIF SUR LINKEDIN\".
Voici le texte au format JSON :
"""
os.environ['OPENAI_PREPROMPT'] = pre_prompt
OPENAI_PREPROMPT = os.environ['OPENAI_PREPROMPT']

openai.api_key = OPENAI_API_KEY 
notion = Client(auth=NOTION_API_KEY)
HEADERS_RAPID_API = {
            "X-RapidAPI-Host": "fresh-linkedin-profile-data.p.rapidapi.com",
            "X-RapidAPI-Key": X_RAPID_API_KEY
            }
URL_RAPID_API_ACTIVITY_POST = "https://fresh-linkedin-profile-data.p.rapidapi.com/get-profile-posts"
URL_RAPID_API_ACTIVITY_PROFILE = "https://fresh-linkedin-profile-data.p.rapidapi.com/get-linkedin-profile"

clients = []

def get_notion_clients():
    page = notion.databases.query(
    **{
        "database_id": NOTION_DB_ID,
        "filter": {
            "timestamp": "created_time",
            "created_time": {
            "past_week": {}
            }
        },
    }
    )
    for res in page['results']:
        name = res['properties']['Name']['title'][0]['plain_text']
        linkedin = res['properties']['LinkedIn']['url']
        page_id = res['id']
        
        client = {
             "name" : name,
             "linkedin_url" : linkedin,
             "page_id" : page_id,
        }
        clients.append(client)
       

def save_analysis_to_notion(client):
    if client['ai_analysis'] != None:
        notion.pages.update(
            client['page_id'], properties={"AI_helper":
                { 
                    "rich_text":[
                        {
                        "type": "text",
                        "text": {
                            "content": client['ai_analysis']
                            }
                        }   
                    ]
                },
                "Linkedin activity" : 
                        { 
                    "select":
                            {
                            "name": client['linkedin_activity'][0],
                            "color":  client['linkedin_activity'][1],
                        }   
                    }
            }
        )
        print("Updating Notion property")

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def generate_summarizer(
    max_tokens=100,
    temperature=0.5,
    top_p=0.5,
    frequency_penalty=0.5,
    prompt = "Nothing"
):
    activites_json = json.dumps(prompt, indent=2, ensure_ascii=False)
    print(activites_json)
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.5,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.1,
        messages=
       [
         {
          "role": "user",
          "content": OPENAI_PREPROMPT + activites_json,
         }
        ],
    )
    return res["choices"][0]["message"]["content"]
    
def get_linkedin_info_for(url, headers, client_url, types = ["posts", "comments", "reactions"]):
    responses = {}
    for t in types:
        response = requests.get(url, headers=headers, params={"linkedin_url": client_url, "type": t})
        data = response.json()['data']
        responses[t] = [item for item in data]
    return responses

def get_human_freshness_from_interaction(t):
    freshness = re.split('(\d+)', t)
    numbers = ""
    alphabets = ""
    for i in freshness:
        if i >= '0' and i <= '9':
            numbers += i
        else:
            alphabets += i
    laps = "années"
    if alphabets == "mo":
        laps = "mois"
    if alphabets == "d":
        laps = "jours"
    if alphabets == "w":
        laps = "semaines"
        
    if laps == "années":
        pp("Not taking this interaction cause it's too old...")
        return False
    else:    
        return numbers + " " + laps

def filter_linkedin_activities(linkedin_activities):
    mapping_human_name = {"posts": "posts rédigés par l'utilisateur",
                          "comments": "posts commentés (mais non rédigé) par l'utilisateur",
                          "reactions": "post ayant fait réagir l'utilisateur (mais non rédigés par l'utilisateur)"
                          }
    linkedin_activity = {"posts rédigés par l'utilisateur" : [],
                         "posts commentés (mais non rédigé) par l'utilisateur" : [],
                         "post ayant fait réagir l'utilisateur (mais non rédigés par l'utilisateur)" : []
                         }
    token_length = 0
    for key in mapping_human_name:
        
        for item in linkedin_activities[key]:
            item.setdefault("acticle_title", "")
            item.setdefault("acticle_subtitle", "")
            item.setdefault("text", "")
            item.setdefault("time", "") 
            freshness_ok = get_human_freshness_from_interaction(item['time'])
            
            if freshness_ok:
                activity = {
                            "titre du post" : item["acticle_title"],
                            "sous-titre du post": item["acticle_subtitle"],
                            "texte du post" : item["text"],
                            "fraicheur du post": freshness_ok
                }
                token_length += len(json.dumps(activity, indent=2, ensure_ascii=False))
                if token_length >= abs(4095 - len(json.dumps(activity, indent=2, ensure_ascii=False))):
                    return(linkedin_activity)
                else:
                    linkedin_activity[mapping_human_name[key]].append(
                            activity
                        )
    # print(linkedin_activity)
    return(linkedin_activity)
        

def get_linkedin_activities(client):
    time.sleep(1)
    linkedin_activities = get_linkedin_info_for(URL_RAPID_API_ACTIVITY_POST, HEADERS_RAPID_API, client['linkedin_url'])
    print("studying linkedin prospect "+client['page_id'])
    client["activités utilisateurs"] = filter_linkedin_activities(linkedin_activities)
        
def get_linkedin_bio(client):
    print("Getting client's bio "+client['name'])
    response = requests.get(URL_RAPID_API_ACTIVITY_PROFILE, headers=HEADERS_RAPID_API, params={"linkedin_url": client['linkedin_url']})
    
    result = response.json()
    result.setdefault("Data", "")
    if "Data" in result:
        data = response.json()['Data']
        client['bio'] = data['about']
    else:
        client['bio'] = ""

def analyze_clients_with_ai(client):
    client_id = client['page_id']
    print("\nAnalyzing prospect "+client_id+"'s activities with OpenAI...")
    result = generate_summarizer(prompt = client)
    client["ai_analysis"] = None
    if result.find("UTILISATEUR NON ACTIF SUR LINKEDIN") == -1:
        print("Client's worth analyzing")
        client["ai_analysis"] = result
        client['linkedin_activity'] = ('Active', 'green')
        
    else:
        client["ai_analysis"] = ""
        client['linkedin_activity'] = ('Inactive', 'red')
        
def print_clients(slice_clients):
    for client in clients[0:slice_clients]:
        print("Within client "+client['name'])

if __name__ == '__main__':
    get_notion_clients()
    slice_clients = len(clients)
    for client in clients[0:slice_clients]:
        get_linkedin_bio(client)
        get_linkedin_activities(client)
        analyze_clients_with_ai(client)
        save_analysis_to_notion(client)
    