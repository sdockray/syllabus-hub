# syllabus-hub

This is a website for a syllabus sharing community - a "GitHub for syllabi."

It imagines a syllabus a bit like software, as a product of collective intellectual labor, as a score to be interpreted or acted out in different contexts.

Technically, it is a Flask front end that uses Gitlab as a backend via the Gitlab API. Gitlab/Github can be confusing to people who are non-programmers and a lot of the interface is irrelevant to syllabi, so this project strips it down to the essentials in order to build back up. Right now, it features a syllabus list, markdown editing, simplified creation, and syllabus cloning. I think that revision history, branching, adding licenses, issues (as discussions), and possibly merge requests or groups could all be interesting things to implement (all of which are fairly easy through the API).

This project comes out of conversations with many people at The Public School including especially Chandler McWilliams and Caleb Waldorf.

### Installation

```
git clone http://github.com/sdockray/syllabus-hub
virtualenv venv 
source venv/bin/activate
pip install -r requirements.txt
```

then you have to create a config file
```
nano app.conf
```
and make sure the following are defined:
```
SECRET_KEY = 'change me to anything'
GIT_SERVER = 'http://your.gitlab.server'
GIT_PRIVATE_TOKEN = 'rootUserPrivateToken'
PORT = 5001
```
