import { GrpcClient } from "../k6_test/grpc/grpc_client.js";

{{k6_opts}}

const sharedClient = new GrpcClient({
  grpcHost: '{{base_url}}'
});
const inputsData = JSON.parse(open(`../k6_test/payloads/{{payload}}`));
let params = {
  tags: { model_name: `{{model_name}}` },
}

export default () => {
  const data = {
    "model_name": "{{model_name}}",
    "inputs": inputsData["inputs"]
  };
  sharedClient.infer(data, params);
};

export function teardown() {
  sharedClient.close();
};
