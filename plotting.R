library(ggplot2)
library(cowplot)
library(latex2exp)
library(stringr)

filename = "mary-fal18"

# Function to get the number of students in an instance
get_student_count <- function(filename){
  file_path = paste("output\\",filename,"_table6.csv",sep="")
  student_count <- length(read.csv(file_path, skip = 1, header = FALSE))-2
  return(student_count)
}


# Function to create data frame
produce_dataframe <- function(filename){
  file_path = paste("output\\",filename,"_table6.csv",sep="")
  data <- read.csv(file_path, skip = 1, header = FALSE)
  student_count <- get_student_count(filename)
  orderings <- c("B1,B2,B3","B1,B3,B2","B2,B1,B3","B2,B3,B1","B3,B1,B2","B3,B2,B1")
  metrics <- c("elective","conflict","mode")
  processed_dataframe <- data.frame(ordering = rep(orderings, each = 3),metric = rep(metrics,6))
  for (s in 1:student_count){
    student_data <- data[s+2]
    processed_dataframe <- cbind(processed_dataframe, student_data)
    names(processed_dataframe)[length(names(processed_dataframe))] <- s
  }
  return(processed_dataframe)
}


# Function to pick out a vector for a specific ordering and metric
find_vector_data <- function(data,choose_ordering,choose_metric){
  find_subset <- subset(data, ordering == choose_ordering & metric == choose_metric)[,-c(1:2)]
  vector_data <- c()
  for (i in colnames(find_subset)){vector_data <- append(vector_data,mean(find_subset[[i]]))}
  return(vector_data)
}

# Function that produces a barplot for the percentage metrics
create_bar_plot_lower <- function(df,ordering_choice,metric_choice){
  data_for_count = find_vector_data(df,ordering_choice,metric_choice)
  percentage_groups <- c("[0,20)","[20-40)","[40-60)","[60-80)","[80-100]")
  percentage_count <- c(0,0,0,0,0)
  for(i in 1:student_count){
    test_value <- data_for_count[i]
    if (test_value < 20) {
      percentage_count[1] <- percentage_count[1]+1
    } else if (20 <= test_value & test_value < 40) {
      percentage_count[2] <- percentage_count[2]+1
    } else if (40 <= test_value & test_value < 60) {
      percentage_count[3] <- percentage_count[3]+1
    } else if (60 <= test_value & test_value < 80) {
      percentage_count[4] <- percentage_count[4]+1
    } else {
      percentage_count[5] <- percentage_count[5]+1
    }
  }
  bar_plot_data <- data.frame(head(percentage_groups,-1),head(percentage_count,-1))
  colnames(bar_plot_data) <- c("Percentage range","Number of students")
  p<-ggplot(data=bar_plot_data, aes(x=`Percentage range`, y=`Number of students`)) +
    geom_bar(stat="identity",fill="black") +
    ggtitle(TeX(paste("Ordering: ",ordering2tex(ordering_choice), sep = " ")))+
    theme_bw()+
    scale_y_continuous(breaks=c(0,5,10,15,20,25,30,35),limits=c(0,35))
  return(p)
}

# Function that produces a barplot for the percentage metrics
create_bar_plot <- function(df,ordering_choice,metric_choice){
  data_for_count = find_vector_data(df,ordering_choice,metric_choice)
  percentage_groups <- c("[0,20)","[20-40)","[40-60)","[60-80)","[80-100]")
  percentage_count <- c(0,0,0,0,0)
  for(i in 1:student_count){
    test_value <- data_for_count[i]
    if (test_value < 20) {
      percentage_count[1] <- percentage_count[1]+1
    } else if (20 <= test_value & test_value < 40) {
      percentage_count[2] <- percentage_count[2]+1
    } else if (40 <= test_value & test_value < 60) {
      percentage_count[3] <- percentage_count[3]+1
    } else if (60 <= test_value & test_value < 80) {
      percentage_count[4] <- percentage_count[4]+1
    } else {
      percentage_count[5] <- percentage_count[5]+1
    }
  }
  bar_plot_data <- data.frame(percentage_groups,percentage_count)
  colnames(bar_plot_data) <- c("Percentage range","Number of students")
  p<-ggplot(data=bar_plot_data, aes(x=`Percentage range`, y=`Number of students`)) +
    geom_bar(stat="identity",fill="black") +
    ggtitle(paste("Ordering:",ordering_choice, sep = " "))+
    theme_bw()+
    ylim(0,student_count)
  return(p)
}

# Function that produces a barplot for the conflicts
create_bar_plot_conflictsonly <- function(df,ordering_choice){
  data_for_count = find_vector_data(df,ordering_choice,"# Conflicts")
  groups <- c("0","1","2","3+")
  count <- c(0,0,0,0)
  for(i in 1:student_count){
    test_value <- data_for_count[i]
    if (test_value == 0) {
      count[1] <- count[1]+1
    } else if (test_value == 1) {
      count[2] <- count[2]+1
    } else if (test_value == 2) {
      count[3] <- count[3]+1
    } else {
      count[4] <- count[4]+1
    }
  }
  bar_plot_data <- data.frame(groups,count)
  colnames(bar_plot_data) <- c("Number of conflicts","Number of students")
  p<-ggplot(data=bar_plot_data, aes(x=`Number of conflicts`, y=`Number of students`)) +
    geom_bar(stat="identity",fill="black") +
    ggtitle(paste("Ordering:",ordering_choice, sep = " "))+
    theme_bw()+
    ylim(0,student_count)
  return(p)
}

# Function that produces a barplot for the conflicts
create_bar_plot_conflictsonly_finer <- function(df,ordering_choice){
  data_for_count = find_vector_data(df,ordering_choice,"conflict")
  groups <- c("0","1","2","3+")
  count <- c(0,0,0,0)
  for(i in 1:student_count){
    test_value <- data_for_count[i]
    if (test_value == 0) {
      count[1] <- count[1]+1
    } else if (test_value == 1) {
      count[2] <- count[2]+1
    } else if (test_value == 2) {
      count[3] <- count[3]+1
    } else {
      count[4] <- count[4]+1
    }
  }
  bar_plot_data <- data.frame(groups[-1],count[-1])
  colnames(bar_plot_data) <- c("Number of conflicts","Number of students")
  p<-ggplot(data=bar_plot_data, aes(x=`Number of conflicts`, y=`Number of students`)) +
    geom_bar(stat="identity",fill="black") +
    ggtitle(TeX(paste("Ordering: ",ordering2tex(ordering_choice), sep = " ")))+
    theme_bw()+
    scale_y_continuous(breaks=c(0,5,10,15,20,25,30),limits=c(0,30))
  return(p)
}

# Turning an ordering into tex format
ordering2tex <- function(ordering){
  lst <- unlist(strsplit(ordering,""))
  #return(paste("$",lst[1],"_",lst[2],lst[3],lst[4],"_",lst[5],lst[6],lst[7],"_",lst[8],"$",sep=""))
  return(paste("$","z","_",lst[2],lst[3],"z","_",lst[5],lst[6],"z","_",lst[8],"$",sep=""))
}

# Actually doing things
df <- produce_dataframe(filename)
orderings <- unique(df$ordering)
metrics <- unique(df$metric)
student_count <- get_student_count(filename)


# Plots

metric_choice = metrics[1]
p12 <- create_bar_plot_lower(df,orderings[1],metric_choice)
p22 <- create_bar_plot_lower(df,orderings[2],metric_choice)
p32 <- create_bar_plot_lower(df,orderings[3],metric_choice)
p42 <- create_bar_plot_lower(df,orderings[4],metric_choice)
p52 <- create_bar_plot_lower(df,orderings[5],metric_choice)
p62 <- create_bar_plot_lower(df,orderings[6],metric_choice)
grid <- plot_grid(
  p12, p22, p32, p42, p52, p62,
  ncol = 2
)
title_gg <- ggdraw() + 
  draw_label(paste("Count of students who attend a percent of their classes (",filename,")",sep="")) +
  theme_void()
dev.new(width=8.5, height=11, unit="in")
plot_grid(
  title_gg, grid,
  ncol = 1,
  rel_heights = c(0.1, 1)
)

p1 <- create_bar_plot_conflictsonly_finer(df,orderings[1])
p2 <- create_bar_plot_conflictsonly_finer(df,orderings[2])
p3 <- create_bar_plot_conflictsonly_finer(df,orderings[3])
p4 <- create_bar_plot_conflictsonly_finer(df,orderings[4])
p5 <- create_bar_plot_conflictsonly_finer(df,orderings[5])
p6 <- create_bar_plot_conflictsonly_finer(df,orderings[6])
grid <- plot_grid(
  p1, p2, p3, p4, p5, p6,
  ncol = 2
)
title_gg <- ggdraw() + 
  draw_label(paste("Count of students with a certain number of conflicts (",filename,")",sep="")) +
  theme_void()
dev.new(width=8.5, height=11, unit="in")
plot_grid(
  title_gg, grid,
  ncol = 1,
  rel_heights = c(0.1, 1)
)
