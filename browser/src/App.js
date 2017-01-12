import React from 'react';
import logo from './logo.png';
import axios from 'axios';
import './App.css';


class Tweet extends React.Component {
  render() {
    var tweet = this.props.tweet
    return (
      <div key={tweet.text} className="tweet">
        <a href={tweet.url}>
          {tweet.text}
        </a>
        {tweet.images.map(function(image) {
          return (
            <div key={image}>
            <a href={tweet.url}>
              <img alt={tweet.text} src={image}/>
            </a>
            </div>
          );
        })}
      </div>
    )}
}

// sheet of twitter matches of the supplied input
class TwitterOutput extends React.Component {
  constructor(props) {
    super(props)
    this.state = {tweets:[], source:props.source}
  }

  loadJobs(source) {
    console.log("loadJobs:");
    console.log("source:", source);
    var th = this;
    th.abortCurrentRequest();
    var CancelToken = axios.CancelToken;
    th.cancelTokenSource = CancelToken.source();
    axios.get(source, {cancelToken:th.cancelTokenSource.token})
    .then(function(result) {
      console.dir(result)
      delete th.cancelTokenSource;
      th.setState({
        tweets: result.data.ret.ret
      });
    })
    .catch(function(err) {
      if (err instanceof axios.Cancel) {
        console.log("cancels are expected, see abortCurrentRequest()");
      } else {
        console.log("unexepected error from axios.get(source), source:", source, "err:")
        console.dir(err);
      }
    });
  }
  componentDidMount() {
    console.log("componentDidMount");
    var source = this.state.source;
    this.loadJobs(source);
  }

  componentWillReceiveProps(nextProps) {
    console.log("componentWillReceiveProps:");
    console.dir(nextProps);
    this.setState(nextProps);
    if (nextProps.hasOwnProperty('source')) {
      this.setState({tweets:[]}); // tweets are unknown since the source has changed
      this.loadJobs(nextProps.source);
    }
  }

  abortCurrentRequest() {
    if (this.hasOwnProperty('cancelTokenSource')) {
      console.dir(this.cancelTokenSource);
      this.cancelTokenSource.cancel();
      delete this.cancelTokenSource;
    }
  }

  componentWillUnmount() {
    this.abortCurrentRequest()
  }

  render() {
    console.log("output render")
    return (
      <div>
        <h1>Tweets!</h1>
        {this.state.tweets.map(function(tweet) {
          return (
            <Tweet key={tweet.url} tweet={tweet} />
          );
        })}
      </div>
    )
  }
}

class TwitterInput extends React.Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.state = {keyword: this.props.keyword}
  }

  handleChange(e) {
    console.log("handleChange, value:", e.target.value)
    this.setState({keyword: e.target.value});
  }

  handleSubmit(e) {
    const keyword = this.state.keyword
    console.log('A keyword submitted: ' + keyword);
    this.props.onChange(keyword);
    e.preventDefault()
  }

  render() {
    const keyword = this.state.keyword;
    return (
      <form onSubmit={this.handleSubmit}>
        <label>
          Keyword:
          <input type="text" value={keyword} onChange={this.handleChange} />
        </label>
        <input type="submit" value="Submit" />
      </form>
    );
  }
}

// Single page app
class Page extends React.Component {
  constructor(props) {
    super(props);
    this.handleKeywordChange = this.handleKeywordChange.bind(this);
    this.state = {keyword: 'coffee'};
  }

  handleKeywordChange(keyword) {
    console.log('handleKeywordChange:', keyword);
    this.setState({keyword: keyword});
  }

  render() {
    const word = this.state.keyword
    const url = process.env.REACT_APP_API_ENDPOINT_URL + '?word=' + word
    console.log('url:', url)
    return (
      <div>
        <TwitterInput keyword={word} onChange={this.handleKeywordChange}/>
        <TwitterOutput source={url}/>
      </div>
    )
  }
}

class AppError extends React.Component {
  render() {
    return (
      <div className="App">
        <div className="App-error">
          <img src={logo} className="App-logo" alt="logo" />
          <h2>Welcome to Keyword</h2>
          <p>before running or building this program you must set the environment variable that identifies the keyword URL.  Something like this:</p>
          <p></p>
          <p>$export REACT_APP_API_ENDPOINT_URL=https://cr3fsvbvt3.execute-api.us-west-2.amazonaws.com/v1/keyword </p>
        </div>
      </div>
    );
  }
}

class App extends React.Component {
  render() {
    console.log("process.env.REACT_APP_API_ENDPOINT_URL:", process.env.REACT_APP_API_ENDPOINT_URL)
    if (typeof process.env.REACT_APP_API_ENDPOINT_URL === 'undefined') {
      return (<AppError/>);
    }
    var endpointUrl = process.env.REACT_APP_API_ENDPOINT_URL
    return (
      <div className="App">
        <div className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h2>Welcome to Keyword</h2>
          <p>endpoint: {endpointUrl}</p>
        </div>
        <Page source={endpointUrl}/>
      </div>
    );
  }
}

export default App;
