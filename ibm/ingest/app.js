var express = require('express');
var path = require('path');
var favicon = require('serve-favicon');
var logger = require('morgan');
var cookieParser = require('cookie-parser');
var bodyParser = require('body-parser');

var index = require('./routes/index');
var users = require('./routes/users');

var app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'jade');

// uncomment after placing your favicon in /public
//app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

app.use('/', index);
app.use('/users', users);

///////////////////////
// get the app environment from Cloud Foundry

// last 10 tweets
var createCache = function(length){
    var pointer = 0, cache = [];
    return {
        push : function(item){
            if (cache.length < length) {
                pointer = cache.push(item) % length;
            } else {
                cache[pointer] = item;
                pointer = (pointer +1) % length;
            }
        },
        get  : function(){
            if (cache.length < length) {
                return cache;
            } else {
                return cache.slice(pointer, length).concat(cache.slice(0, pointer));
            }
        }
    };
};

var tweetBuffer = createCache(10);
var env =  process.env;
console.log(JSON.stringify(env, null, '  '));

app.get('/dump', function (req, res) {
    var dump = {
        twitter: tweetBuffer.get(),
        env: env
    };
    var dumpString = JSON.stringify(dump, null, '  ');
    res.send('<h1>last 10 tweets and environment:</h1><pre>' + dumpString + "</pre>");
});

// twitter
if ((process.env.TWITTER_CONSUMER_KEY === undefined) ||
    (process.env.TWITTER_CONSUMER_SECRET === undefined) ||
    (process.env.TWITTER_ACCESS_TOKEN === undefined) ||
    (process.env.TWITTER_ACCESS_SECRET === undefined)) {
    console.log('need to set the TWITTER environment variables defined');
    process.exit(-1);
}
var Twitter = require('twitter');
var client = new Twitter({
    consumer_key: process.env.TWITTER_CONSUMER_KEY,
    consumer_secret: process.env.TWITTER_CONSUMER_SECRET,
    access_token_key: process.env.TWITTER_ACCESS_TOKEN,
    access_token_secret: process.env.TWITTER_ACCESS_SECRET
});

var stream = client.stream('statuses/filter', {track: 'coffee,ibm,javascript'});
stream.on('data', function(event) {
    if (event) {
        tweetBuffer.push(event);
        console.log(event && event.text);
    }
});

stream.on('error', function(error) {
    console.log(error);
    throw error;
});

/////////////////////////////////////////////

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  var err = new Error('Not Found');
  err.status = 404;
  next(err);
});

// error handler
app.use(function(err, req, res/*, next*/) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

module.exports = app;
