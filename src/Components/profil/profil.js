import React, { useState } from 'react';
import './profil.css';
import Store from '../../store/store';
import { Redirect } from 'react-router-dom';
import Trackers from './trackers';
import SetWindow from './setWindow';

const Profil = (props) => {

    let loginState = Store.getState()

    const [state, changeState] = useState({
        displayNewTracker: false,
        dataFromChild: null,
    })

    const newTrackerHandler = () => {
        changeState((prevState) => ({
            ...prevState,
            displayNewTracker: !state.displayNewTracker,
        }))
        console.log(state)
    }

    const showTrackerHandler = (data) => {
        changeState((prevState) => ({
            ...prevState,
            dataFromChild: data,
        }))
    }


    const content = 
        <div className="Profil">
            <Trackers passed={showTrackerHandler}/>
            <button className="Addnew" onClick={newTrackerHandler}>Přidat nový</button>
            <div className="OutputFrame">
                {state.displayNewTracker ? <SetWindow closeClick={newTrackerHandler}/> : <div className="Placeholder">Vyberte tracker
                nebo zvolte "Přidat nový"</div>}
            </div>
            
        </div>

    const gtfo = <Redirect to='/'/>
                

    return (
        <React.Fragment>
        {loginState.logged
        ? content
        : gtfo}
        </React.Fragment>
    )
}

export default Profil;