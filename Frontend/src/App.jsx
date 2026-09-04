import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./App.css";
import Chat from "./Pages/Chat";
import Checkout from "./Pages/Checkout";
import Cart from "./Pages/Cart";

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
          path="/commerce/chat/session/:sessionId"
          element={<Chat />}
        />

        <Route
          path="/checkout"
          element={<Checkout />}
        />

        <Route
          path="/cart"
          element={<Cart />}
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;