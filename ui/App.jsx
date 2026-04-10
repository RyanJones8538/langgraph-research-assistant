import { use, useEffect, useState } from "react";
import OutputDisplay from "./components/OutputDisplay";
import StreamingDisplay from "./components/StreamingDisplay";
import UserInput from "./components/UserInput";
import VariableDisplay from "./components/VariableDisplay";

export default function App() {
  const [output, setOutput] = useState("");
  const [streamingOutput, setStreamingOutput] = useState("");
  const [variables, setVariables] = useState({});

  useEffect(() => {

    }, []);

    return (
        <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
            <h1>LangGraph Research Assistant</h1>
            <table>
                <tr>
                    <td><OutputDisplay output={output} /></td>
                    <td><StreamingDisplay output={streamingOutput} /></td>
                </tr>
                <tr>
                    <td><UserInput onSubmit="cat" /></td>
                    <td><VariableDisplay variables={variables} /></td>
                </tr>
            </table>
        </div>
    );
}