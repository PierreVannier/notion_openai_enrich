# notion_openai_enrich
Enrich Notion field with OpenAI analysis
This is a small hack that parse one notion DB for clients with linkedin url to enrich these clients with relevant information (taken from OpenAI analysis with GPT-3.5).

The idea is to be able to get a client's relevant linkedin activities at a glance in notion.
## ⚠ Still heavy WIP

# Install
One has to setup a few details prior to installing.
I use the following Rapid API https://rapidapi.com/freshdata-freshdata-default/api/fresh-linkedin-profile-data in order to fetch profile information and interactions (like comments, posts, reactions).

You'll also need to create an OpenAI account.

Your notion DB should have a filed with "linkedin_url" :
```
client = {
             "name" : name,
             "linkedin_url" : linkedin,
             "page_id" : page_id,
        }
```

You need to setup your keys in a .env file (not versioned for obvious reasons)

Best is to create a virtual env (conda or venv), then :
```
pip install -r requirements.txt
```