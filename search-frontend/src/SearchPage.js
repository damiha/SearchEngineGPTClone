import React, { useState } from 'react';

const SearchPage = () => {
    const [searchString, setSearchString] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);

    const HighlightText = ({ searchString, snippet }) => {
        if (!searchString.trim()) return <p>{snippet}</p>;
    
        // Split the search string into words and remove punctuation
        const searchWords = searchString.split(/\s+/).map(word => word.replace(/[^\w\s]|_/g, "").toLowerCase());
    
        // Function to test if a word matches any search word
        const isMatch = word => searchWords.includes(word.toLowerCase().replace(/[^\w\s]|_/g, ""));
    
        // Split the snippet into words while keeping punctuation intact
        const words = snippet.split(/(\b\w+\b)/);
    
        return (
            <p>
                {words.map((word, index) => 
                    isMatch(word) ? <b key={index}>{word}</b> : word
                )}
            </p>
        );
    };

    const handleSearch = async () => {
        try {
            const response = await fetch('http://127.0.0.1:5000/search_engine/get_urls', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ search_string: searchString, lang_code: language}),
            });
            const data = await response.json();
            setSearchResults(data.message);
        } catch (error) {
            console.error('Error fetching search results:', error);
        }
    };

    const handlePageChange = (direction) => {
        setCurrentPage(prev => direction === 'next' ? prev + 1 : prev - 1);
    };

    const resultsPerPage = 10;
    const paginatedResults = searchResults.slice((currentPage - 1) * resultsPerPage, currentPage * resultsPerPage);

    const [language, setLanguage] = useState('en');

    return (
        <div className="search-page">
            <div className="search-bar">
                <input
                    type="text"
                    value={searchString}
                    onChange={(e) => setSearchString(e.target.value)}
                    className="search-input"
                />
                <input
                    type="text"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="language-input"
                    maxLength="3"
                />
                <button onClick={handleSearch} className="search-button">Search</button>
            </div>
            <div className="results">
                {paginatedResults.map((result, index) => (
                    <div key={index} className="result-box">
                        <a href={result.url}>{result.url}</a>
                        <p>date: {result.date}</p>
                        <HighlightText searchString={searchString} snippet={result.snippet} />
                        <p>language: {result.language.language}, contains: {result.contains.join(", ")}</p>
                    </div>
                ))}
            </div>
            {searchResults.length > resultsPerPage && (
                <div className="pagination">
                    {currentPage > 1 && (
                        <button onClick={() => handlePageChange('prev')} className="page-button">Previous</button>
                    )}
                    <span className="page-number">{currentPage}</span>
                    {currentPage * resultsPerPage < searchResults.length && (
                        <button onClick={() => handlePageChange('next')} className="page-button">Next</button>
                    )}
                </div>
            )}
        </div>
    );
};

export default SearchPage;
