from flask import Flask, render_template, request, jsonify, Response
import redditAPI
from rq import Queue
from rq.job import Job
from worker import conn
import time, json

q = Queue(connection=conn)

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def home():
    return render_template('index.html')


@app.route('/enqueue', methods=['GET', 'POST'])
def enq():
    data = request.get_json()
    print(data)
    job = q.enqueue(redditAPI.main, data['postNum'], data['commNum'])
    return {'job_id': job.id}

@app.route('/get_data', methods=['GET', 'POST'])
def get_data():
    return "WHAT"

@app.route('/progress/<string:job_id>')
def progress(job_id):
    def get_status():

        job = Job.fetch(job_id, connection=conn)
        status = job.get_status()
        
        while status != 'finished':

            status = job.get_status()
            job.refresh()

            d = {'status': status}

            if 'progress' in job.meta:
                d['value'] = job.meta['progress']
            else:
                d['value'] = 0
                
            # IF there's a result, add this to the stream
            if job.result:
                d['result'] = job.result

            json_data = json.dumps(d)
            yield f"data:{json_data}\n\n"
            time.sleep(1)


    return Response(get_status(), mimetype='text/event-stream')
    

if __name__ == '__main__':
    app.run(port=8080)