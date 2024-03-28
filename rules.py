import onnx
 
def find_with_input_node(model, name):
    for node in model.graph.node:
        if len(node.input) > 0 and name in node.input:
            return node
 
def find_all_with_input_node(model, name):
    all = []
    for node in model.graph.node:
        if len(node.input) > 0 and name in node.input:
            all.append(node)
    return all
 
def find_with_output_node(model, name):
    for node in model.graph.node:
        if len(node.output) > 0 and name in node.output:
            return node
 
def find_with_no_change_parent_node(model, node):
    parent = find_with_output_node(model, node.input[0])
    if parent is not None:
        if parent.op_type in ["Concat", "MaxPool"]:
            return find_with_no_change_parent_node(model, parent)
    return parent
 
def find_quantizelinear_conv(model, qnode):
    dq   = find_with_input_node(model, qnode.output[0])
    conv = find_with_input_node(model, dq.output[0])
    return conv
 
 
def find_quantize_conv_name(model, weight_qname):
    dq = find_with_output_node(model, weight_qname)
    q  = find_with_output_node(model, dq.input[0])
    return ".".join(q.input[0].split(".")[:-1])
 
def find_quantizer_pairs(onnx_file):
 
    model = onnx.load(onnx_file)
    match_pairs = []
    for node in model.graph.node:   
        if node.op_type == "Concat":
            qnodes = find_all_with_input_node(model, node.output[0])
            major = None
            for qnode in qnodes:
                if qnode.op_type != "QuantizeLinear":
                    continue
                 
                conv = find_quantizelinear_conv(model, qnode)
                if major is None:
                    major = find_quantize_conv_name(model, conv.input[1])
                else:
                    match_pairs.append([major, find_quantize_conv_name(model, conv.input[1])])
 
                for subnode in model.graph.node:
                    if len(subnode.input) > 0 and subnode.op_type == "QuantizeLinear" and subnode.input[0] in node.input:
                        subconv = find_quantizelinear_conv(model, subnode)
                        match_pairs.append([major, find_quantize_conv_name(model, subconv.input[1])])
 
        elif node.op_type == "MaxPool":
            qnode = find_with_input_node(model, node.output[0])
            if not (qnode and qnode.op_type == "QuantizeLinear"):
                continue
 
            major = find_quantizelinear_conv(model, qnode)
            major = find_quantize_conv_name(model, major.input[1])
            same_input_nodes = find_all_with_input_node(model, node.input[0])
 
            for same_input_node in same_input_nodes:
                if same_input_node.op_type == "QuantizeLinear":
                    subconv = find_quantizelinear_conv(model, same_input_node)
                    match_pairs.append([major, find_quantize_conv_name(model, subconv.input[1])])
    return match_pairs
