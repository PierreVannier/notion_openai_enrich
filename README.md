# notion_openai_enrich
Enrich Notion field with OpenAI analysis
This is a small hack that parse one notion DB for clients with linkedin url to enrich these clients with relevant information (taken from OpenAI analysis with GPT-3.5).

The idea is to be able to get a client's relevant linkedin activities at a glance in notion.

# Install
One has to setup a few details prior to installing.
I use the following Rapid API https://rapidapi.com/freshdata-freshdata-default/api/fresh-linkedin-profile-data in order to fetch profile information and interactions (like comments, posts, reactions).
You'll also need to create an OpenAI account.

```
# necessary secrets
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
NOTION_API_KEY = os.getenv('NOTION_API_KEY', None)
X_RAPID_API_KEY = os.getenv('X_RAPID_API_KEY', None)
NOTION_DB_ID = os.getenv("NOTION_DB_ID", None)
OPENAI_PREPROMPT = os.getenv("OPENAI_PREPROMPT", None)
```

Best is to create a virtual env (conda or venv), then :
```
pip install -r requirements.txt
```