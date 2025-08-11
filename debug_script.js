// Debug script to test metadata loading
console.log('Debug script running...');

async function debugMetadata() {
    console.log('Starting metadata debug...');
    
    try {
        const url = 'docs/data/metadata.json';
        console.log('Fetching from:', url);
        
        const response = await fetch(url);
        console.log('Response:', {
            status: response.status,
            ok: response.ok,
            headers: [...response.headers.entries()]
        });
        
        if (response.ok) {
            const text = await response.text();
            console.log('Raw response text:', text.substring(0, 200) + '...');
            
            try {
                const metadata = JSON.parse(text);
                console.log('Parsed metadata:', metadata);
                
                if (metadata.match_statistics) {
                    const count = metadata.match_statistics.matches_with_handgun_data;
                    console.log('Match count:', count);
                    console.log('Formatted:', count.toLocaleString());
                } else {
                    console.error('No match_statistics in metadata');
                }
            } catch (parseError) {
                console.error('JSON parse error:', parseError);
            }
        } else {
            console.error('HTTP error:', response.status, response.statusText);
        }
    } catch (fetchError) {
        console.error('Fetch error:', fetchError);
    }
}

// Run immediately
debugMetadata();