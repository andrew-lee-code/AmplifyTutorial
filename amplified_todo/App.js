import { useState, useEffect } from "react";
import { Alert, StatusBar, StyleSheet, Text, View } from "react-native";
import { Amplify, API } from "aws-amplify";
import { withAuthenticator } from "aws-amplify-react-native";
import awsconfig from "./src/aws-exports";

import Home from "./src/Home";
import { ComponentPropsToStylePropsMap } from "@aws-amplify/ui-react";

Amplify.configure(awsconfig);

const App = () => {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const getData = async () => {
      try {
        setIsLoading(true);
        const apiName = "todoLayerAPI";
        const path = "/layer/todo";
        const myInit = {
          body: {
            test: "This description has been changed from the POST request",
          },
          headers: {}, // OPTIONAL
          response: true, // OPTIONAL (return the entire Axios response object instead of only response.data)
          // queryStringParameters: {
          //   // OPTIONAL
          //   name: "param",
          // },
        };
        API.post(apiName, path, myInit)
          .then((response) => {
            console.log(response);
          })
          .catch((error) => {
            console.log("************ERROR**************");
            console.log(error);
          });
        // API.get(apiName, path, myInit)
        //   .then((response) => {
        //     console.log(response);
        //   })
        //   .catch((error) => {
        //     console.log("************ERROR**************");
        //     console.log(error);
        //   });
        setIsLoading(false);
      } catch (e) {
        Alert.alert("Error getting  data", e.message);
        logger.info(`Failed to get data with error: ${e.message}`);
      }
    };

    getData();
  }, []);

  if (isLoading) {
    return (
      <View style={styles.container}>
        <Text>Loading...</Text>
      </View>
    );
  }
  return (
    <View style={styles.container}>
      <StatusBar />
      <Text>Hello World</Text>
      {/* <Home /> */}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#fff",
    flex: 1,
  },
});

export default withAuthenticator(App);
