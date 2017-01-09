import React, { Component } from 'react';
import logo from './logo.png';
import axios from 'axios';
import './App.css';

/*
function Welcome(props) {
  return <h1>Hello, {props.name}</h1>;
}
*/

class Welcome extends Component {
  render() {
    return (
      <h1>Hello2, {this.props.name}</h1>
    );
  }
}


class Floor extends Component {
  render() {
    return (
      <div>
        <Welcome name="Sara" />
        <Welcome name="Cahal" />
        <Welcome name="Edite" />
      </div>
    );
  }
}

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
/*
      <Floor />
*/
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
    return (
      <div className="App">
        <div className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h2>Welcome to Keyword</h2>
        </div>
        <div>
            <Wall source="https://3kaszefv3c.execute-api.us-west-2.amazonaws.com/v1/keyword"/>
        </div>
      </div>
    );
  }
            /* <Wall source="http://codepen.io/jobs.json"/> */

}



export default App;

