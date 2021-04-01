# Prevention-of-Cyber-Troll-Sarcasm-System-on-Social-Networking-using-ML-with-Bilingual-Analytics
The virtual social media managing platform will help the user to analyse the comments received on the posts created by the user. The current system used for monitoring social media platforms is manually analysing comments and deleting negative comments or manually blocking a regular spammer or hate promotor. This web application will eliminate the effort required to manually screen thousands of comments and block hundreds of spam users. The user has to register to the application and then provide permission to the web application for accessing his account by authenticating via the OAuth platform. The application then retrieves the comments on the posts.  The suitable algorithms for sentiment analysis and sarcasm are applied on the comments and displays the aggregated results on the panel home. The user can search for specific posts and view analytics for those posts. The platform can also provide auto-replies for positive comments and reports/blocks negative comments.  The application also blocks spam users.  Hence, this application will highly contribute towards reducing online hate and help influencers to manage their social media profiles.
***
### Steps for running the source code

1. Clone the repo and navigate to source_code folder.

2. Download the glove embeddings file from the [drive link](https://drive.google.com/file/d/1Lh7W538MowOk7UTsI-jD2n4VI25ZZdOf/view?usp=sharing)
and place it in the 'data' directory.

Note : Do not rename it.

3. Save "client_secret.json" file in vmanager.

4. Go to "vmanager" and save ".env" file containing twitter api keys.

5. Go to "vmanager/models" and create a folder called "hinglish" and save all 3 model files(config.json, tf_model.h5, tf_model.preproc) in it.

6. Create a virtual environment for the project.

```
python -m venv env
```
Run this command only once i.e for the first time when you use this project.

7. Activate the virtual environment by entering the command below in command prompt.

```
.\env\Scripts\activate
```

8. Install dependencies
```
pip install -r requirements.txt
```

9. Edit twitter.py for flask dance

Go to env -> lib -> flask dance -> contrib -> twitter.py
change base_url value in line 60 to
base_url="https://api.twitter.com/",
( beware of indentation)

10. To create database (from "source_code") run the following in cmd.

```
python 

from vmanager.models import User

from vmanager import db

db.create_all()
```

11. To avoid auto adjustment of import statements in VSCode.

In VSCode, "Cntrl + Shift + p" -> command palette opens up -> type "settings.json" (Open Settings) -> add the following line and save. 

```
"python.formatting.autopep8Args": ["--ignore","E402"] 
```


9. Go to source_code directory in cmd and launch the Flask web app by running the following command.

```
python run.py
```

***

<h3 align="center"><b>Developed with :heart: by <a href="https://github.com/tejaskaria">Tejas Karia</a>,<a href="https://github.com/priya-mane"> Priya Mane</a>,<a href="https://github.com/JeetMehta99"> Jeet Mehta</a> and <a href="https://github.com/pratik6725">Pratik Merchant</a>.</b></h1>