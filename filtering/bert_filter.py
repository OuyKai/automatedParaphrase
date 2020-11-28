from transformers import BertTokenizer, BertModel, BertConfig
from sentence_transformers import SentenceTransformer
import torch
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

""" BERT Word embeddings for similarity """

def concatenate_output(outputs):
    """
    Concatenate the last four hidden layer output
    :param outputs: BERT model output
    :return a vector formed by the concatenation of the output of the last four hidden layer
    """
    
    token_vecs_cat = []
    # For each token in the sentence...
    for token in outputs[0]:
        # Concatenate the vectors (that is, append them together) from the last four layers
        cat_vec = torch.cat((token[-1], token[-2], token[-3], token[-4]), dim=0)
        
        # Use `cat_vec` to represent `token`.
        token_vecs_cat.append(cat_vec)

    return token_vecs_cat


###########################################################################################################################
## Pooling STrategy function from Chris McCkormick page: https://mccormickml.com/2019/05/14/BERT-word-embeddings-tutorial/
###########################################################################################################################

def layer_concatenation(outputs):
    """
    Concatenate the last four hidden layer for each token into one vecotr output
    :param outputs: BERT model output, 
    :return a vector formed by the concatenation of the output of the last four hidden layer for each token
    """
    # Here output is Float.Tensor: outputs[0]= last_hidden_state; outputs[1]= pooler_output; outputs[2]= hidden_states;
    # More details: https://huggingface.co/transformers/model_doc/bert.html#bertmodel  and https://colab.research.google.com/drive/1yFphU6PW9Uo6lmDly_ud9a6c4RCYlwdX#scrollTo=HKTlTS_sfuAe

    # in order to get sentence embeddings I have to adopt a pooling strategy. The idea is to combine hidden_states vector, hidden states has four dimensions, in the following order:
    #    1. The layer number (13 layers) - layers dimension
    #    2. The batch number (1 sentence)
    #    3. The word / token number (22 tokens in our sentence) -tokens dimension 
    #    4. The hidden unit / feature number (768 features)
    
    # Here the adopted strategy is to concatenate the last four layer for each token. Concatenate the last four layers, giving us a single word vector per token
    hidden_states = outputs[2]

    token_embeddings = torch.stack(hidden_states, dim=0) # Combine the layers to make this one whole big tensor
    token_embeddings = torch.squeeze(token_embeddings, dim=1) # remove "batches" dimension since we don't need it
    token_embeddings = token_embeddings.permute(1,0,2) # swap/switching "layers" and "tokens" dimensions

    token_vecs_cat = []
    
    #token_embeddings = token_embeddings[1:] # remove [CLS] token embedding vector
    #token_embeddings = token_embeddings[:-1] # remove [SEP]  token embedding vectorand 
    #token_embeddings = token_embeddings[1:-1] # remove [CLS] and [SEP] token embedding vector
    
    # For each token in the sentence...
    for token in token_embeddings:
        # Concatenate the the last four layers of the current token
        cat_vec = torch.cat((token[-1], token[-2], token[-3], token[-4]), dim=0)
        
        # append current vector
        token_vecs_cat.append(cat_vec)
    
    return token_vecs_cat

def summing_layer(outputs):
    """
    Sum the vectors from the last four layers.
    :param outputs: BERT model output, 
    :return a vector formed by the summation of the last four hidden layer of the hidden_states
    """
    # Here output is Float.Tensor: outputs[0]= last_hidden_state; outputs[1]= pooler_output; outputs[2]= hidden_states;
    # More details: https://huggingface.co/transformers/model_doc/bert.html#bertmodel  and https://colab.research.google.com/drive/1yFphU6PW9Uo6lmDly_ud9a6c4RCYlwdX#scrollTo=HKTlTS_sfuAe

    # in order to get sentence embeddings I have to adopt a pooling strategy. The idea is to combine hidden_states vector, hidden states has four dimensions, in the following order:
    #    1. The layer number (13 layers) - layers dimension
    #    2. The batch number (1 sentence)
    #    3. The word / token number (22 tokens in our sentence) -tokens dimension 
    #    4. The hidden unit / feature number (768 features)
    
    # Here the adopted strategy is to concatenate the last four layer for each token. Concatenate the last four layers, giving us a single word vector per token
    hidden_states = outputs[2]

    token_embeddings = torch.stack(hidden_states, dim=0) # Combine the layers to make this one whole big tensor
    token_embeddings = torch.squeeze(token_embeddings, dim=1) # remove "batches" dimension since we don't need it
    token_embeddings = token_embeddings.permute(1,0,2) # swap/switching "layers" and "tokens" dimensions

    token_vecs_sum = []

    # `token_embeddings` is a [words x 12 x 768] tensor.
    token_embeddings = token_embeddings[1:-1] # remove [CLS] and [SEP] token embedding vector

    # For each token in the sentence...
    for token in token_embeddings:

        # `token` is a [12 x 768] tensor

        # Sum the vectors from the last four layers. sum_vec = torch.sum(token[-4:], dim=0)
        sum_vec = torch.sum(token[:], dim=0)
        
        # Use `sum_vec` to represent `token`.
        token_vecs_sum.append(sum_vec)
        
    return token_vecs_sum

def second_to_last_layer_average(outputs):
    """
    Average the second to last hiden layer of each token
    :param outputs: BERT model output, 
    :return a 768 length vector formed by averaging the second to last layer of the hidden_states 
    """
    # Here output is Float.Tensor: outputs[0]= last_hidden_state; outputs[1]= pooler_output; outputs[2]= hidden_states;
    # More details: https://huggingface.co/transformers/model_doc/bert.html#bertmodel  and https://colab.research.google.com/drive/1yFphU6PW9Uo6lmDly_ud9a6c4RCYlwdX#scrollTo=HKTlTS_sfuAe

    # in order to get sentence embeddings I have to adopt a pooling strategy. The idea is to combine hidden_states vector, hidden states has four dimensions, in the following order:
    #    1. The layer number (13 layers) - layers dimension
    #    2. The batch number (1 sentence)
    #    3. The word / token number (22 tokens in our sentence) -tokens dimension 
    #    4. The hidden unit / feature number (768 features)
    
    # Here the adopted strategy is to concatenate the last four layer for each token. Concatenate the last four layers, giving us a single word vector per token
    hidden_states = outputs[2] # `hidden_states` has shape [13 x 1 x 22 x 768]
    # `token_vecs` is a tensor with shape [22 x 768]
    token_vecs = hidden_states[-2][0] # get
    # Calculate the average of all 22 token vectors.
    sentence_embedding = torch.mean(token_vecs, dim=0)

    # torch.mean() example:
    #  
    # a = tensor([[-0.3841,  0.6320,  0.4254, -0.7384],
    #             [-0.9644,  1.0131, -0.6549, -1.4279],
    #             [-0.2951, -1.3350, -0.7694,  0.5600],
    #             [ 1.0842, -0.9580,  0.3623,  0.2343]])
    #
    # >>> torch.mean(a, dim = 0)
    # >>> tensor([-0.0163, -0.5085, -0.4599,  0.1807])
    # In our function sentence_embedding will be a tensor of sitorch.Size() = 768
    return sentence_embedding #the worst pooling strategy for semantic similarity


def average_of_layer_average(outputs):
    """
    Averaging the average of each layer tokens.
    :param outputs: BERT model output, 
    :return a 768 length vector formed by averaging the average embedding of each layer tokens 
    """
    # Here the adopted strategy is to concatenate the last four layer for each token. Concatenate the last four layers, giving us a single word vector per token
    hidden_states = outputs[2] # `hidden_states` has shape [13 x 1 x 22 x 768]
    
    # # `token_vecs` is a tensor with shape [22 x 768]
    # token_vecs = hidden_states[-1][0] # get
    # # Calculate the average of all 22 token vectors.
    # sentence_embedding = torch.mean(token_vecs, dim=0)
    sentence_embedding = []
    
    for layers in hidden_states: # to get the first 4 layers => hidden_states[0:4]
        # layer is of size torch.Size([1,X,768]), where X is the number of tokens in the sentences
        token_layer = layers[0] # get current layer tokens embeddings => get X embeddings
        for token_embedding in token_layer: # get token embedding except [CLS] and [SEP] tokens => token_layer[1:-1]
            layer_average = torch.mean(token_embedding, dim=0) # average current layer, e.g. if [3x768] => [768] vector by averaging the 3 row togheter
        sentence_embedding.append(layer_average)

    sentence_embedding = torch.stack(sentence_embedding)
    sentence_embedding = torch.mean(sentence_embedding, dim=0)

    return sentence_embedding

###########################################################################################################################


def token_vector_sum(token_embeddings): 
    """
    Summing togheter all token embedding
    :param token_embeddings: a list of token embeddings
    :return a vector formed by the summation of all token embeddings
    """

    sum_vec = torch.sum(token_embeddings,dim=0)
    return sum_vec

def token_vector_mean(token_embeddings):#return a sentence vecotr as the mean average of all token vector
    """
    Get the mean average of all token embedding
    :param token_embeddings: a list of token embeddings
    :return a vector formed by the mean average of all token embeddings
    """

    # sum_vec = torch.sum(token_embeddings[1:-2],dim=0)#sum of all token except the first([CLS]=0) and the last token([SEP] = -1)
    sentence_embedding = torch.mean(token_embeddings, dim=0)
    return sentence_embedding

def get_encoded_layers(utterance,model,tokenizer):#huggingface transformers library embeddings
    """
    Get BERT embedding of a sentence using the Huggingface transformers
    :param utterance: the sentence to embed
    :param model: Huggingface transformers BERT model
    :param tokenizer: Huggingface transformers BERT Tokenizer
    :return Huggingface transform BERT model output consisting of tuple(torch.FloatTensor) comprising various elements depending on the configuration (BertConfig) and inputs
    """
    input_ids = torch.tensor(tokenizer.encode(utterance, add_special_tokens=True)).unsqueeze(0)

    with torch.no_grad():
        encoded_layers = model(input_ids)
        return encoded_layers
        

def get_similarity(vector1,vector2):
    """
    Apply cosine similarity on BERT embeddings vector
    :param vector1: embedding of the first sentence 
    :param model: embedding of the second sentence 
    :return the cosine similarity between vecotr1 and vector2
    """
    a = vector1[0].reshape(1,-1)
    a = a.detach().numpy()
    b = vector2[0].reshape(1,-1)
    b = b.detach().numpy()

    cos_lib = cosine_similarity(a,b)
    return np.asscalar(cos_lib)#convert numpy array to float


def bert_selection(pool):#ebeddings using Huggingface trandformers library
    """
    Remove paraphrases that are not semantically equivalent to the initial expression and duplicate(filtering+deduplication)
    :param pool: a Python dictionary, Key is the initial expression, value is a set of paraphrases
    :return a Python dictionary where not semantically equivalent paraphrases and duplicate are removed
    """
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    # to get hidden layer in the output uncomment the following above code line, see https://huggingface.co/transformers/model_doc/bert.html for details
    # model = BertForPreTraining.from_pretrained('bert-base-uncased')
    # config = BertConfig.from_pretrained("bert-base-uncased", output_hidden_states=True)
    # model = BertModel.from_pretrained("bert-base-uncased", config=config) #return hidden state in the output
    model = BertModel.from_pretrained("bert-base-uncased",output_hidden_states = True)
    model.eval()
    
    result = dict()
    for key,value in pool.items():
        a = get_encoded_layers(key,model,tokenizer)
        vector1 = chris(a)

        # token_embeddings = a[0][0]
        # vectora = token_vector_sum(a[0][0])
        # vectora2 = token_vector_mean(a[0][0])
        paraphrases = []
        for candidate in value:
            b = get_encoded_layers(candidate,model,tokenizer)
            vector2 = chris(b)

            # token_embeddings = b[0][0]
            # vectorb = token_vector_sum(b[0][0])
            # vectorb2 = token_vector_mean(b[0][0])
            cos_sim = get_similarity(vector1,vector2)
            # cos_sim2 = ukplab_similarity(vectora,vectorb)
            if cos_sim > 0.5 and cos_sim <= 0.95:
                paraphrases.append((candidate,cos_sim))
        result[key] = paraphrases
    return result

def bert_filtering(pool):#ebeddings using Huggingface trandformers library
    """
    Remove paraphrases that are not semantically equivalent to the initial expression 
    :param pool: a Python dictionary, Key is the initial expression, value is a set of paraphrases
    :return a Python dictionary where not semantically equivalent paraphrases are removed
    """
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    # to get hidden layer in the output uncomment the following above code line, see https://huggingface.co/transformers/model_doc/bert.html for details
    # model = BertForPreTraining.from_pretrained('bert-base-uncased')
    # config = BertConfig.from_pretrained("bert-base-uncased", output_hidden_states=True)
    # model = BertModel.from_pretrained("bert-base-uncased", config=config) #return hidden state in the output
    model = BertModel.from_pretrained("bert-base-uncased")
    model.eval()
    
    result = dict()
    for key,value in pool.items():
        a = get_encoded_layers(key,model,tokenizer)
        vector1 = concatenate_output(a)

        # token_embeddings = a[0][0]
        # vectora = token_vector_sum(a[0][0])
        # vectora2 = token_vector_mean(a[0][0])
        paraphrases = []
        for candidate in value:
            b = get_encoded_layers(candidate,model,tokenizer)
            vector2 = concatenate_output(b)

            # token_embeddings = b[0][0]
            # vectorb = token_vector_sum(b[0][0])
            # vectorb2 = token_vector_mean(b[0][0])
            cos_sim = get_similarity(vector1,vector2)
            # cos_sim2 = ukplab_similarity(vectora,vectorb)
            if cos_sim > 0.5:
                paraphrases.append(candidate)
        result[key] = paraphrases
    return result

def bert_deduplication(pool):#remove deduplicate paraphrases
    """
    Remove paraphrases that are duplication of the initial expression 
    :param pool: a Python dictionary, Key is the initial expression, value is a set of paraphrases
    :return a Python dictionary where duplicate paraphrases are removed
    """

    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertModel.from_pretrained("bert-base-uncased")
    model.eval()
    result = dict()
    for key,value in pool.items():
        a = get_encoded_layers(key,model,tokenizer)
        vector1 = concatenate_output(a)

        # token_embeddings = a[0][0]
        # vectora = token_vector_sum(a[0][0])
        # vectora2 = token_vector_mean(a[0][0])
        paraphrases = []
        for candidate in value:
            b = get_encoded_layers(candidate,model,tokenizer)
            vector2 = concatenate_output(b)

            # token_embeddings = b[0][0]
            # vectorb = token_vector_sum(b[0][0])
            # vectorb2 = token_vector_mean(b[0][0])
            cos_sim = get_similarity(vector1,vector2)
            if cos_sim <= 0.95:
                paraphrases.append(candidate)
        result[key] = paraphrases
    return result


def ukplab_similarity(vector1,vector2):
    """
    Cosine similarity using UKPLab sentence-transformers library  embeddings vector
    :param vector1: UKPLab sentence-transformers embedding of sentence 1
    :param vector1: UKPLab sentence-transformers embedding of sentence 2
    :return cosine similarity between vector1 and vector2
    """
    a = vector1.reshape(1,-1)
    # b = embedding_output2.reshape(1,-1)
    b = vector2.reshape(1,-1)
    cos_lib = cosine_similarity(a,b)
    return np.asscalar(cos_lib)#convert numpy array to float

def get_embeddings(utterance,embedder):# embeddings using UKPLab sentence_transformers library
    """
    UKPLab sentence-transformers  sentence embeddings
    :param utterance: sentence to embed
    :param embedder: UKPLab sentence-transformers model
    :return sentence embedding using UKPLab sentence-transformers library
    """

    sentence_embeddings = embedder.encode(utterance)
    return sentence_embeddings

def ukplab_filtering(pool):#embeddings using UKPLab sentence_transformers library
    """
    Remove paraphrases that are not semantically equivalent to the initial expression using the UKPLab sentence-transformers library 
    :param pool: a Python dictionary, Key is the initial expression, value is a set of paraphrases
    :return a Python dictionary where not semantically equivalent paraphrases are removed
    """

    embedder = SentenceTransformer('bert-base-nli-mean-tokens')
    result = dict()
    for key,value in pool.items():
        a = get_embeddings(key,embedder)
        vector1 = a[0]
        print(key)
        paraphrases = []
        for candidate in value:
            b = get_embeddings(candidate,embedder)
            vector2 = b[0]
            cos_sim = ukplab_similarity(vector1,vector2)
            if cos_sim > 0.5:
                paraphrases.append(candidate)
                print(key,",",candidate,"= ",cos_sim)
        result[key] = paraphrases
    return result


if __name__ == "__main__":
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    # to get hidden layer in the output uncomment the following above code line, see https://huggingface.co/transformers/model_doc/bert.html for details
    # model = BertForPreTraining.from_pretrained('bert-base-uncased')
    # config = BertConfig.from_pretrained("bert-base-uncased", output_hidden_states=True)
    # model = BertModel.from_pretrained("bert-base-uncased", config=config) #return hidden state in the output
    model = BertModel.from_pretrained("bert-base-uncased",output_hidden_states = True) # model = BertModel.from_pretrained("bert-base-uncased",output_hidden_states = True
    model.eval()
    
    u1 = "how"
    u2 = "how did covid-19 spread"
    a = get_encoded_layers(u1,model,tokenizer)
    vector1 = second_to_last_layer_average(a)

    # token_embeddings = a[0][0]
    # vectora = token_vector_sum(a[0][0])
    # vectora2 = token_vector_mean(a[0][0])
    
    b = get_encoded_layers(u2,model,tokenizer)
    vector2 = second_to_last_layer_average(b)

    # token_embeddings = b[0][0]
    # vectorb = token_vector_sum(b[0][0])
    # vectorb2 = token_vector_mean(b[0][0])
    cos_sim = get_similarity(vector1,vector2)
    print(cos_sim)