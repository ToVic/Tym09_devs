import React, { useState, useEffect } from 'react';
import './trackers.css';
import SingleTracker from './singleTracker';
import axios from '../../axios-firebase';




const Trackers = (props) => {

    const [state, changeState] = useState({
        data: [],
    })


    useEffect(() => {
        axios.get('https://testwebapp-3ab8b-default-rtdb.europe-west1.firebasedatabase.app/realquik.json')
        .then((response) => {
            changeState((prevState) => ({
                ...prevState,
                data: response.data ? response.data : [],
            }));
        })
        .catch((error) => {
            console.log(`An error occured with the following description: ${error}`)
        })
        console.log("UPDATING STATE")
    }, [])


    const listingHandler = () => {
        axios.get('https://testwebapp-3ab8b-default-rtdb.europe-west1.firebasedatabase.app/realquik.json')
        .then((response) => {
            changeState((prevState) => ({
                ...prevState,
                data: response.data ? response.data : [],
            }));
        })
        .catch((error) => {
            console.log(`An error occured with the following description: ${error}`)
        })
    }



    return (
        <div className="Trackers" dataTransfer={state.trackerClicked}>
            <h3>Hlídače</h3>
            <p className="Refresh" onClick={listingHandler}>obnovit seznam</p>
            {Object.keys(state.data).length>0 ? null : <p className="RefreshAlert">Obnovte seznam nebo vytvořte hlídače</p>}
            {Object.keys(state.data).map(item => (
                <SingleTracker name={state.data[item].name} key={state.data[item].name}
                    clicked={() => props.passed(state.data[item], item)}/>
                ))}
        </div>
    )
}

export default Trackers;