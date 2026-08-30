import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";
import Chat from "./Pages/Chat";
import Checkout from "./Pages/Checkout";

function App() {

  return (
    <BrowserRouter>

      <Routes>

        <Route
          path="/"
          element={<Chat />}
        />

        <Route
          path="/chat"
          element={<Chat />}
        />

        <Route
          path="/checkout"
          element={<Checkout />}
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;