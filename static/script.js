let redditIdNum = 0;
let newsIdNum = 0;

const progressbar = $('#myProgress');


function update(text) {
    $('#status').text("..." + text);

}

function pp() {

    $('#btn').hide();
    $('.table-wrapper').hide();
    $('#status').show();
    $('.loader').show();

    $.ajax({
        url: window.location.href + '/enqueue',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            'value': "Starting Analysis Job",
            'postNum': $('#postNum').val(),
            'commNum': $('#commNum').val()
        }),
        timeout: 3000,
        success: (function(data) {

            // The job.id returned from the server once enqueued:
            job_id = data['job_id'];

            const source = new EventSource("/progress/" + job_id);

            source.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log("DATAAAAAA: ", data);

                update(data['value'])

                if (data['status'] == 'finished') {
                    $('#btn').show();
                    $('#status').hide();
                    $('.loader').hide();

                    source.close();

                    pp_short(data['result']);
                }
            }

        }),
        error: (function(data) {
            console.log(data);
        })

    });


}

function pp_short(data) {

    console.log("YOOOOOOO: ", data)
    postData = data.postData;
    newsData = data.newsData;


    for (dataItem of postData) {
        if (dataItem.subjects.length == 0) continue;

        let postText = dataItem.comment;
        let senti = dataItem.sentiment;
        let style = '';

        if (senti > 0) style = 'style="color: green"';
        else if (senti < 0) style = 'style="color: red"';
        else style = 'style="color: black"';

        $('#redditCardWrapper').append('\
                    <div class="card">\
                        <div class="card-body">\
                            <h5 class="card-subtitle">Sentiment: <span ' + style + '>' + senti + '</span></h5>\
                            <p>' + postText + '</p>\
                            <h5 class="card-subtitle">Subjects</h5>\
                            <div class="horizontal-scroll">\
                                <ul id="redditSub' + redditIdNum + '">\
                                </ul>\
                            </div>\
                        </div>\
                    </div>');

        $('#redditSub' + redditIdNum).append('<li>' + dataItem.subjects.join('</li><li>') + '</li>');
        redditIdNum++;
    }

    for (dataItem of newsData) {
        if (dataItem.subjects.length == 0) continue;

        let postText = dataItem.news;
        let senti = dataItem.sentiment;
        let style = '';

        if (senti > 0) style = 'style="color: green"';
        else if (senti < 0) style = 'style="color: red"';
        else style = 'style="color: black"';
        $('#newsCardWrapper').append('\
                    <div class="card">\
                        <div class="card-body">\
                            <h5 class="card-subtitle">Sentiment: <span ' + style + '>' + senti + '</span></h5>\
                            <p>' + postText + '</p>\
                            <h5 class="card-subtitle">Subjects</h5>\
                            <div class="horizontal-scroll">\
                                <ul id="newsSub' + newsIdNum + '">\
                                </ul>\
                            </div>\
                        </div>\
                    </div>');

        $('#newsSub' + newsIdNum).append('<li>' + dataItem.subjects.join('</li><li>') + '</li>');
        newsIdNum++;

    }

    restext = JSON.stringify(data.result);
    restext.replace('/{/', '');
    restext.replace('/}/', '');
    restext.replace('/,/', ' ');
    restext.replace('/"/', '');
    console.log(restext);

    $('#infoBox').append('<h3 id="resText">' + restext + '</h3>')
        // document.getElementById("result").innerHTML = data;
    console.log(data);
    $('.loader').hide();
    $('.table-wrapper').show();
    // }
    // });
}