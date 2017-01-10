import React, { Component } from 'react';
import logo from './logo.png';
import axios from 'axios';
import './App.css';

class Wall extends Component {
  constructor(props) {
    super(props)
    this.state = {jobs:[]}
  }

  componentDidMount() {
    // Is there a React-y way to avoid rebinding `this`? fat arrow?
    console.log("componentDidMount")
    var th = this;
    this.serverRequest =
      axios.get(this.props.source)
      .then(function(result) {
        console.dir(result)
        th.setState({
          jobs: result.data.ret
        });
      })
  }

  componentWillUnmount() {
    this.serverRequest.abort();
  }

  render() {
    return (
      <div>
        <h1>Jobs!</h1>
        {this.state.jobs.map(function(job) {
          return (
            <div key={job.text} className="job">
              <a href={job.url}>
                {job.tet}
                is looking for a 
                {job.tet}
                {job.tet}
              </a>
            </div>
          );
        })}
      </div>
/*
*/

    )
  }
}

class App extends Component {
  render() {
    console.log("process.env.REACT_APP_API_ENDPOINT_URL:", process.env.REACT_APP_API_ENDPOINT_URL)
    if (typeof process.env.REACT_APP_API_ENDPOINT_URL === 'undefined') {
      return (
        <div className="App">
          <div className="App-header">
            <img src={logo} className="App-logo" alt="logo" />
            <p>Welcome to Keyword</p>
            <p>before running or building this program you must set the environment variable that identifies the keyword URL.  Something like this:</p>
            <p></p>
            <p>$export REACT_APP_API_ENDPOINT_URL=https://cr3fsvbvt3.execute-api.us-west-2.amazonaws.com/v1/keyword </p>
          </div>
        </div>
      );
    } else {
      return (
        <div className="App">
          <div className="App-header">
            <img src={logo} className="App-logo" alt="logo" />
            <h2>Welcome to Keyword</h2>
          </div>
          <div>
              <Wall source={process.env.REACT_APP_API_ENDPOINT_URL}/>
          </div>
        </div>
      );
    }
  }
            /* <Wall source="http://codepen.io/jobs.json"/> */

}



export default App;

