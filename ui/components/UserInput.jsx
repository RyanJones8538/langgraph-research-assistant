export default function UserInput({ onSubmit }) {
    const [input, setInput] = useState("");

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(input);
        setInput("");
    };

    return (
        <form onSubmit={handleSubmit}>
            <input>
                label="Enter your research topic here..."
                id="topic"
                value={input}
            </input>   
        </form>
    );
}