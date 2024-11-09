from flask import Flask, render_template, jsonify
from confluent_kafka import Consumer, KafkaException
import threading
import time

app = Flask(__name__)

# Initialize global variables
total_chars = 0
word_count = {}

# Stop words list (common words to exclude from the word count)
stop_words = set([
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren', 'as', 'at', 'be', 'because',
    'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'cannot', 'could', 'couldn', 'couldnt', 'did', 'didn',
    'didnt', 'do', 'does', 'doesn', 'doesnt', 'doing', 'don', 'don’t', 'dont', 'had', 'hadn', 'hadnt', 'has', 'hasn', 'hasnt', 'have',
    'haven', 'havent', 'having', 'he', 'he’d', 'he’ll', 'he’s', 'here', 'here’s', 'hereafter', 'hereby', 'herein', 'here’s', 'hers', 'herself',
    'him', 'himself', 'his', 'how', 'how’s', 'howsoever', 'how’s', 'i', 'i’d', 'i’ll', 'i’m', 'i’ve', 'i’dnt', 'i’d', 'i’ll', 'is', 'isn',
    'isnt', 'it', "it's", 'it’ll', 'it\'s', 'ive'
])



# Kafka Consumer Configuration
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',  # Replace with your Kafka broker address
    'group.id': 'flask-consumer-group',  # Consumer group ID
    'auto.offset.reset': 'earliest',  # Start reading from the earliest message
}

consumer = Consumer(consumer_conf)

# Ensure stop words are being excluded before updating word count
def process_message(message):
    global total_chars, word_count
    if message.value() is None:
        return

    # Decode the message value (Kafka message body)
    line = message.value().decode('utf-8')
    total_chars += len(line)  # Increment total characters processed

    # Split the line into words and update the word count
    words = line.split()
    for word in words:
        word = word.lower()  # Normalize to lowercase
        if word not in stop_words and word.isalpha():  # Exclude stop words and non-alphabetic characters
            word_count[word] = word_count.get(word, 0) + 1  # Update word count

    print(f"Processed message: {line}")
    print(f"Total characters: {total_chars} | Word counts: {word_count}")


# Consumer loop to consume Kafka messages in real-time
def consume_messages():
    try:
        consumer.subscribe(['file-streaming'])  # Subscribe to the Kafka topic (replace 'file-streaming' with your topic)

        while True:
            msg = consumer.poll(timeout=1.0)  # Poll for messages every second

            if msg is None:  # No message received
                continue
            elif msg.error():  # Handle Kafka error
                print(f"Error received: {msg.error()}")
                raise KafkaException(msg.error())
            else:
                process_message(msg)  # Process the received message

    except KeyboardInterrupt:
        print("Consumer stopped by user.")
    finally:
        consumer.close()  # Close the consumer when done

@app.route('/')
def index():
    # Sort and get the top 5 words by frequency
    sorted_words = sorted(word_count.items(), key=lambda item: item[1], reverse=True)
    top_words = [(i, item) for i, item in enumerate(sorted_words[:5])]  # Top 5 words
    all_words = [(i, item) for i, item in enumerate(sorted_words[:20])]  # All words (limited to 20)
    
    # Debug print statement
    print(f"Total characters: {total_chars}")
    print(f"Top words: {top_words}")
    print(f"All words: {all_words}")

    return render_template('index.html', total_chars=total_chars, top_words=top_words, all_words=all_words)


@app.route('/stats')
def stats():
    # Return stats as JSON
    sorted_words = sorted(word_count.items(), key=lambda item: item[1], reverse=True)
    top_words = sorted_words[:20]
    
    return jsonify({'total_chars': total_chars, 'top_words': top_words})

def start_kafka_consumer():
    # Start Kafka consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_messages)
    consumer_thread.daemon = True
    consumer_thread.start()

if __name__ == "__main__":
    start_kafka_consumer()  # Start Kafka consumer
    app.run(debug=True, host='0.0.0.0', port=5000)  # Run Flask app
