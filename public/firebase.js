
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.14.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/9.14.0/firebase-analytics.js";
const firebaseConfig = {
//TODO: hide api key?
  apiKey: "AIzaSyCIBc-ULdO-bwAkhwQ21JZ2n1j94YC1jMQ",
  authDomain: "mailbox-60855.firebaseapp.com",
  projectId: "mailbox-60855",
  storageBucket: "mailbox-60855.appspot.com",
  messagingSenderId: "744804758620",
  appId: "1:744804758620:web:8facb319405cb891146299",
  measurementId: "G-ELJLTB28HY"
};
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);