import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import {backendPending} from './services/api';
import './styles.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode>{backendPending && <div role="status" style={{padding:'12px 20px',background:'#fff5df',color:'#8c651d',textAlign:'center',fontSize:12}}>Frontend preview · Backend hosting is pending. Sign-in, document uploads, and research will be available once the backend is connected.</div>}<BrowserRouter><App/></BrowserRouter></React.StrictMode>);
