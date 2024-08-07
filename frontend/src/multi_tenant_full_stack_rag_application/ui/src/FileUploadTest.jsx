//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: MIT-0

import * as React from "react";
import FileUpload from "@cloudscape-design/components/file-upload";
import FormField from "@cloudscape-design/components/form-field";

export default () => {
  const [value, setValue] = React.useState([]);
  return (
    <FormField
      label="Form field label"
      description="Description"
    >
      <FileUpload
        onChange={({ detail }) => setValue(detail.value)}
        value={value}
        i18nStrings={{
          uploadButtonText: e =>
            e ? "Choose files" : "Choose file",
          dropzoneText: e =>
            e
              ? "Drop files to upload"
              : "Drop file to upload",
          removeFileAriaLabel: e =>
            `Remove file ${e + 1}`,
          limitShowFewer: "Show fewer files",
          limitShowMore: "Show more files",
          errorIconAriaLabel: "Error"
        }}
        showFileLastModified
        showFileSize
        showFileThumbnail
        tokenLimit={3}
        constraintText="Hint text for file requirements"
      />
    </FormField>
  );
}